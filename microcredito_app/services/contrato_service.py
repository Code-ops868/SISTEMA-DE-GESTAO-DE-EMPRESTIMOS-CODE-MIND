# microcredito_app/services/contrato_service.py

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import platform

class ContratoService:
    """Serviço para gerar contrato de empréstimo em PDF baseado no modelo fornecido"""
    
    def __init__(self):
        self.font_name = self._get_system_font()
        self.line_height = 14  # Altura padrão da linha
        self.margin_left = 2 * cm
        self.margin_top = 2 * cm
        self.page_width, self.page_height = A4
        self.max_width = self.page_width - 2 * self.margin_left - 1 * cm
        self.y = self.page_height - self.margin_top  # Posição vertical atual
    
    def _get_system_font(self):
        """Detecta e usa fontes do sistema para suporte a acentos"""
        sistema = platform.system()
        fontes = {
            'Windows': ['Arial', 'Times New Roman'],
            'Darwin': ['Helvetica', 'Arial'],
            'Linux': ['DejaVu-Sans', 'Helvetica']
        }
        for nome_fonte in fontes.get(sistema, ['Helvetica']):
            try:
                pdfmetrics.getFont(nome_fonte)
                return nome_fonte
            except:
                pass
        return 'Helvetica'
    
    def _draw_text(self, text, font_size=10, bold=False, spacing=14):
        """Desenha texto com posicionamento automático"""
        self.c.setFont(self.font_name, font_size)
        lines = self._wrap_text(text)
        for line in lines:
            self.c.drawString(self.margin_left, self.y, line)
            self.y -= spacing
    
    def _wrap_text(self, text):
        """Quebra texto em múltiplas linhas"""
        if not text:
            return [""]
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)
            if self.c.stringWidth(line_text, self.font_name, 10) > self.max_width:
                current_line.pop()
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines
    
    def _add_spacing(self, amount=14):
        """Adiciona espaço vertical"""
        self.y -= amount
    
    def _add_new_page(self):
        """Adiciona uma nova página"""
        self.c.showPage()
        self.y = self.page_height - self.margin_top
    
    def gerar_contrato(self, emprestimo):
        """
        Gera o PDF do contrato a partir dos dados do empréstimo
        """
        buffer = io.BytesIO()
        self.c = canvas.Canvas(buffer, pagesize=A4)
        self.y = self.page_height - self.margin_top
        
        # ============================================
        # TÍTULO
        # ============================================
        self.c.setFont(self.font_name, 16)
        self.c.drawCentredString(self.page_width / 2, self.y, "CONTRATO DE EMPRÉSTIMO")
        self.y -= 25
        
        # ============================================
        # OPERADORA (EMPRESA)
        # ============================================
        self.c.setFont(self.font_name, 10)
        empresa = emprestimo.cliente.usuario.empresa
        if empresa:
            nome = empresa.nome
            endereco = empresa.endereco or "cidade de Nampula, Rua de Teté"
            representante = emprestimo.cliente.usuario.get_full_name() or "Representante"
        else:
            nome = "Operadora de Microcrédito"
            endereco = "cidade de Nampula, Rua de Teté"
            representante = "Senhor(a) Representante"
        
        texto = f"Entre a {nome}, com sede na {endereco}, representado neste pela Senhora {representante} na qualidade de administradora,"
        self._draw_text(texto)
        self._draw_text("doravante designado por operadora de microcrédito")
        self._add_spacing(10)
        self._draw_text("E")
        self._add_spacing(10)
        
        # ============================================
        # MUTUÁRIO (CLIENTE)
        # ============================================
        cliente = emprestimo.cliente
        estado_civil = getattr(cliente, 'estado_civil', 'solteiro(a)')
        endereco = cliente.endereco or "Nampula, bairro de [Bairro]"
        telefone = cliente.telefone
        documento = cliente.bi_passaporte or "[Número do Documento]"
        
        # Detectar tipo de documento
        if documento and len(documento) == 13:
            doc_tipo = "BI"
            doc_numero = documento
        elif documento and len(documento) == 9:
            doc_tipo = "DIRE"
            doc_numero = documento
        else:
            doc_tipo = "Passaporte"
            doc_numero = documento
        
        texto = f"{cliente.nome}, {estado_civil}, de Nacionalidade Moçambicana, residente em {endereco}, celular no {telefone},"
        self._draw_text(texto)
        
        data_emissao = cliente.data_emissao_documento.strftime("%d-%m-%Y") if cliente.data_emissao_documento else "[Data de Emissão]"
        data_validade = cliente.data_validade_documento.strftime("%d-%m-%Y") if cliente.data_validade_documento else "[Data de Validade]"
        
        texto = f"Portador do {doc_tipo} no {doc_numero}, emitido aos {data_emissao} pelo arquivo de identificação de Nampula, valido ate {data_validade},"
        self._draw_text(texto)
        self._draw_text("doravante é designado mutuário.")
        self._add_spacing(10)
        
        self._draw_text("É celebrado o presente contrato de empréstimo, que se regerá pelas cláusulas e termos seguintes:")
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 1
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("PRIMEIRA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Valor de empréstimo", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        valor_extenso = self._valor_por_extenso(emprestimo.valor)
        texto = f"Pelo presente, concede-se ao mutuário o valor de {emprestimo.valor:,.2f} MZN ({valor_extenso}) a ser pago em {emprestimo.quantidade_parcelas} ({self._numero_por_extenso(emprestimo.quantidade_parcelas)}) prestações"
        self._draw_text(texto)
        periodicidade = "semanais" if getattr(emprestimo, 'periodicidade', 'semanal') == 'semanal' else "mensais"
        self._draw_text(periodicidade)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 2
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("SEGUNDA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Taxas de juros", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        periodicidade = "semanais" if getattr(emprestimo, 'periodicidade', 'semanal') == 'semanal' else "mensais"
        texto = f"O empréstimo vence juros a taxa de {emprestimo.taxa_juros}%, sendo as prestações de juros {periodicidade}, sucessivas e contadas em forma de prestações mensais sobre o capital em dívida."
        self._draw_text(texto)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 3
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("TERCEIRA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Modo e lugar de reembolso", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        meses = int(emprestimo.quantidade_parcelas / 4) if getattr(emprestimo, 'periodicidade', 'semanal') == 'semanal' else emprestimo.quantidade_parcelas
        
        texto = f"1. O mutuário aceita expressamente devolver o crédito dentro de {meses} ({self._numero_por_extenso(meses)}) meses contados a partir da data de desembolso do crédito bem como de acordo com plano de pagamento em anexo ao contrato."
        self._draw_text(texto)
        
        texto = "2. O mutuário compromete-se ainda, a efectuar os reembolsos do crédito nas contas em anexo no plano de pagamento, apresentando o comprovativo do reembolso junto à sede do operador para que lhe seja passado o recibo que confirma a recepção do valor pelo operador."
        self._draw_text(texto)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 4
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("QUARTA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Vencimento imediato", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        texto = "Pode ser considerado imediatamente vencido o presente contrato exigindo-se de imediatamente, o pagamento de todo o valor de capital e juros, ainda em dívida, bem como todos os outros encargos devidos pelo mutuário a operadora de crédito por força deste empréstimo em qualquer dos casos seguintes:"
        self._draw_text(texto)
        texto = "1. Por falta de pagamento pontual de qualquer das prestações acordadas no plano de pagamento."
        self._draw_text(texto)
        texto = "2. Por infracção de qualquer das cláusulas estabelecidas no presente contrato de empréstimo."
        self._draw_text(texto)
        texto = "3. Omissão de informação bem como a prestação de informação falsa."
        self._draw_text(texto)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 5
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("QUINTA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Garantias do mutuário", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        nome_empresa = empresa.nome if empresa else "Operadora de Microcrédito"
        
        texto = f"1. Para assegurar o reembolso do capital, juros e de mais encargos inerentes ao empréstimo o mutuário constitui garantia para empréstimo recebido a favor da {nome_empresa}, no valor total de 54.000,00 MZN que ficarão na posse do mutuário. Fazem parte integrante das garantias os seguintes bens:"
        self._draw_text(texto)
        
        # Tabela de garantias
        self.c.setFont(self.font_name, 9)
        self._draw_text("Descrição", font_size=9, spacing=12)
        self.c.drawString(self.margin_left + 350, self.y + 12, "Montante")
        self.y -= 12
        self.c.line(self.margin_left, self.y + 4, self.margin_left + 450, self.y + 4)
        self.y -= 6
        
        garantias = [
            ("Dois Congeladores", "12.000,00 MZN"),
            ("Arca", "15.000,00 MZN"),
            ("2 Arcas Brancas", "20.000,00 MZN"),
            ("3 Mesas Plásticas", "1.500,00 MZN"),
            ("12 Cadeiras Plásticas", "1.500,00 MZN"),
            ("Fogão a Gás com Botija", "4.000,00 MZN"),
            ("TOTAL", "54.000,00 MZN")
        ]
        
        for desc, valor in garantias:
            self.c.setFont(self.font_name, 9)
            self.c.drawString(self.margin_left, self.y, desc)
            self.c.drawString(self.margin_left + 350, self.y, valor)
            self.y -= 14
        
        self._add_spacing(10)
        texto = "2. As garantias descritas no número anterior poderão ser usadas em futuros créditos sendo o seu montante actualizado."
        self._draw_text(texto)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 7 - AVALISTA
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("SÉTIMA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Avalista", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        avalista = getattr(emprestimo, 'avalista', None)
        
        if avalista:
            texto = f"O avalista do mutuário {avalista.nome}, natural de {getattr(avalista, 'naturalidade', 'Nampula')}, residente na Cidade de {getattr(avalista, 'residencia', 'Nampula-Muatala')}, portador de BI nr {getattr(avalista, 'numero_documento', '0301007410667B')}, emitido aos {getattr(avalista, 'data_emissao', '15/06/2022')} na cidade de {getattr(avalista, 'local_emissao', 'Nampula')}, compromete-se solidariamente e ilimitada a assumir a responsabilidade que o mutuário tenha contraído com operador caso o mutuário sofra algum impedimento de qualquer natureza que lhe impossibilite de pagar o empréstimo na sua totalidade ou o saldo vigente da dívida com todos os encargos correspondentes. fazem parte dos bens os seguintes:"
        else:
            texto = "O avalista do mutuário [Nome do Avalista], natural de Nampula, residente na Cidade de Nampula-Muatala, portador de BI nr [Número do BI], emitido aos [Data] na cidade de Nampula, compromete-se solidariamente e ilimitada a assumir a responsabilidade que o mutuário tenha contraído com operador caso o mutuário sofra algum impedimento de qualquer natureza que lhe impossibilite de pagar o empréstimo na sua totalidade ou o saldo vigente da dívida com todos os encargos correspondentes. fazem parte dos bens os seguintes:"
        
        self._draw_text(texto)
        
        # Tabela de bens do avalista
        self.c.setFont(self.font_name, 9)
        self._draw_text("Descrição", font_size=9, spacing=12)
        self.c.drawString(self.margin_left + 350, self.y + 12, "Montante")
        self.y -= 12
        self.c.line(self.margin_left, self.y + 4, self.margin_left + 450, self.y + 4)
        self.y -= 6
        
        bens_avalista = [
            ("Congelador Super Star", "5.000,00 MZN"),
            ("1 TV 21p", "2.000,00 MZN"),
            ("TOTAL", "7.000,00 MZN")
        ]
        
        for desc, valor in bens_avalista:
            self.c.setFont(self.font_name, 9)
            self.c.drawString(self.margin_left, self.y, desc)
            self.c.drawString(self.margin_left + 350, self.y, valor)
            self.y -= 14
        
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 7 - ARRESTO E VENDA
        # ============================================
        self.c.setFont(self.font_name, 10)
        texto = "1. O presente penhor pode ser executado logo que, vencida qualquer obrigação que sirva de garantia, verifique mora no ser cumprimento ou ainda quando qualquer um dos bens dado em penhor seja alienado, onerado penhorado, ou objecto de qualquer outra forma apreenção judicial."
        self._draw_text(texto)
        
        texto = "2. O operador fica desde já autorizado caso ocorra qualquer uma das situações previstas no número anterior a proceder a venda extrajudicial dos empenhados a quem melhor intender pelo preço e de mais condições que tenha por convenientes sem dependência a qualquer normalidade cujo fim e reembolsar-se das quantias em dívidas."
        self._draw_text(texto)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 8 - SANÇÕES
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("OITAVA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Sanções", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        texto = "1. Caso se verifique falta de pagamento, pontual das prestações do capital e juros, o mutuário aceita e autoriza o operador a aplicação comulativas das seguintes sanções:"
        self._draw_text(texto)
        
        texto = "2. Pagamento das taxas de juros moratórios diários corresponde a 2% sobre o capital e juros das prestações em atrasos, incluindo os gastos provocados pelas acções de cobranças administrativas legais."
        self._draw_text(texto)
        
        texto = "3. Tomada de imediato dos bens dados mesmo na sua ausência, mediante notificação escrita entregue a qualquer pessoa de maior idade que esteja a residir no local dos bens, bem como avalista familiar autoridade local ou testemunhas idôneas para o efeito."
        self._draw_text(texto)
        self._add_spacing(15)
        
        # ============================================
        # CLÁUSULA 9 - LEI DE FORO
        # ============================================
        self.c.setFont(self.font_name, 12)
        self._draw_text("NONA", font_size=12, spacing=18)
        self.c.setFont(self.font_name, 11)
        self._draw_text("Lei de foro", font_size=11, spacing=18)
        self.c.setFont(self.font_name, 10)
        
        texto = "1. Quaisquer diferendos relacionados com o presente contrato serão resolvidos amigavelmente pelas partes."
        self._draw_text(texto)
        
        texto = "2. Caso as partes não consigam resolver os diferendos nos termos do número anterior, serão exclusivamente competentes o tribunal judicial da cidade de Nampula com renúncia expressa a outros tribunais."
        self._draw_text(texto)
        self._add_spacing(25)
        
        # ============================================
        # ASSINATURAS
        # ============================================
        self.c.setFont(self.font_name, 10)
        self.c.drawString(self.margin_left, self.y, "Assinatura do mutuário")
        self.c.drawString(self.margin_left + 350, self.y, "Assinatura do avalista")
        self.y -= 30
        self.c.line(self.margin_left, self.y, self.margin_left + 150, self.y)
        self.c.line(self.margin_left + 350, self.y, self.margin_left + 500, self.y)
        self.y -= 20
        
        nome_operadora = empresa.nome if empresa else "Operadora de Microcrédito"
        self.c.drawString(self.margin_left, self.y, nome_operadora)
        self.y -= 20
        
        # Data
        data_atual = datetime.now().strftime('%d de %B de %Y')
        meses = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }
        for en, pt in meses.items():
            data_atual = data_atual.replace(en, pt)
        
        self.c.drawString(self.margin_left, self.y, f"Nampula, {data_atual}")
        
        # ============================================
        # FINALIZAR PDF
        # ============================================
        self.c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _valor_por_extenso(self, valor):
        """Converte valor numérico para extenso"""
        try:
            inteiro = int(valor)
            if inteiro >= 1000:
                return f"{inteiro // 1000} mil meticais"
            return f"{inteiro} meticais"
        except:
            return "valor em meticais"
    
    def _numero_por_extenso(self, numero):
        """Converte número para extenso"""
        numeros = {
            1: 'uma', 2: 'duas', 3: 'três', 4: 'quatro', 5: 'cinco',
            6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove', 10: 'dez',
            11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze', 15: 'quinze',
            16: 'dezasseis', 17: 'dezassete', 18: 'dezoito', 19: 'dezanove', 20: 'vinte'
        }
        return numeros.get(numero, str(numero))