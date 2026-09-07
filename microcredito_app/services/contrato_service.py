# microcredito_app/services/contrato_service.py

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import platform

class ContratoService:
    """Serviço para gerar contrato de empréstimo em PDF baseado no modelo fornecido"""
    
    def __init__(self):
        self.font_name = self._get_system_font()
    
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
    
    def gerar_contrato(self, emprestimo):
        """
        Gera o PDF do contrato a partir dos dados do empréstimo
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        margem_esquerda = 2 * cm
        margem_direita = width - margem_esquerda
        y = height - 2 * cm
        self.c = c
        self.width = width
        self.margem_esquerda = margem_esquerda
        
        # ============================================
        # TÍTULO
        # ============================================
        self._titulo(y)
        y -= 30
        
        # ============================================
        # OPERADORA (EMPRESA)
        # ============================================
        y = self._operadora(emprestimo, y)
        y -= 20
        
        # ============================================
        # MUTUÁRIO (CLIENTE)
        # ============================================
        y = self._mutuario(emprestimo, y)
        y -= 20
        
        # ============================================
        # INTRODUÇÃO
        # ============================================
        self._introducao(y)
        y -= 25
        
        # ============================================
        # CLÁUSULAS
        # ============================================
        y = self._clausula_1(emprestimo, y)
        y = self._clausula_2(emprestimo, y)
        y = self._clausula_3(emprestimo, y)
        y = self._clausula_4(y)
        y = self._clausula_5(emprestimo, y)
        y = self._clausula_7_avalista(emprestimo, y)
        y = self._clausula_7_arresto(y)
        y = self._clausula_8(y)
        y = self._clausula_9(y)
        
        # ============================================
        # ASSINATURAS
        # ============================================
        self._assinaturas(emprestimo, y)
        
        # ============================================
        # FINALIZAR PDF
        # ============================================
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _titulo(self, y):
        """Título do contrato"""
        self.c.setFont(self.font_name, 16)
        self.c.drawCentredString(self.width / 2, y, "CONTRATO DE EMPRÉSTIMO")
        self.c.setFont(self.font_name, 10)
    
    def _operadora(self, emprestimo, y):
        """Dados da operadora (empresa)"""
        empresa = emprestimo.cliente.usuario.empresa
        
        if empresa:
            nome = empresa.nome
            endereco = empresa.endereco or "cidade de Nampula, Rua de Teté"
            representante = emprestimo.cliente.usuario.get_full_name() or "Representante"
        else:
            nome = "Operadora de Microcrédito"
            endereco = "cidade de Nampula, Rua de Teté"
            representante = "Senhor(a) Representante"
        
        self.c.setFont(self.font_name, 10)
        texto = f"Entre a {nome}, com sede na {endereco}, representado neste pela Senhora {representante} na qualidade de administradora,"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        self.c.drawString(self.margem_esquerda, y, "doravante designado por operadora de microcrédito")
        y -= 20
        
        self.c.drawString(self.margem_esquerda, y, "E")
        y -= 20
        
        return y
    
    def _mutuario(self, emprestimo, y):
        """Dados do mutuário (cliente)"""
        cliente = emprestimo.cliente
        
        estado_civil = getattr(cliente, 'estado_civil', 'solteiro(a)')
        endereco = cliente.endereco or "Nampula, bairro de [Bairro]"
        telefone = cliente.telefone
        documento = cliente.bi_passaporte or "[Número do Documento]"
        
        # Detectar tipo de documento
        if documento and len(documento) == 13:  # BI (12 dígitos + letra)
            doc_tipo = "BI"
            doc_numero = documento
        elif documento and len(documento) == 9:  # DIRE
            doc_tipo = "DIRE"
            doc_numero = documento
        else:
            doc_tipo = "Passaporte"
            doc_numero = documento
        
        # Nome do cliente
        self.c.setFont(self.font_name, 10)
        texto = f"{cliente.nome}, {estado_civil}, de Nacionalidade Moçambicana, residente em {endereco}, celular no {telefone}"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        # Documento
        data_emissao = cliente.data_emissao_documento.strftime("%d-%m-%Y") if cliente.data_emissao_documento else "[Data de Emissão]"
        data_validade = cliente.data_validade_documento.strftime("%d-%m-%Y") if cliente.data_validade_documento else "[Data de Validade]"
        
        texto = f"Portador do {doc_tipo} no {doc_numero}, emitido aos {data_emissao} pelo arquivo de identificação de Nampula, valido ate {data_validade}"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        self.c.drawString(self.margem_esquerda, y, "doravante é designado mutuário.")
        y -= 25
        
        self.c.drawString(self.margem_esquerda, y, "É celebrado o presente contrato de empréstimo, que se regerá pelas cláusulas e termos seguintes:")
        y -= 25
        
        return y
    
    def _introducao(self, y):
        """Texto de introdução"""
        pass
    
    def _clausula_1(self, emprestimo, y):
        """Cláusula 1 - Valor do empréstimo"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "PRIMEIRA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Valor de empréstimo")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        valor_extenso = self._valor_por_extenso(emprestimo.valor)
        texto = f"Pelo presente, concede-se ao mutuário o valor de {emprestimo.valor:,.2f} MZN ({valor_extenso}) a ser pago em {emprestimo.quantidade_parcelas} ({self._numero_por_extenso(emprestimo.quantidade_parcelas)}) prestações"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        periodicidade = "semanais" if getattr(emprestimo, 'periodicidade', 'semanal') == 'semanal' else "mensais"
        self.c.drawString(self.margem_esquerda, y, periodicidade)
        y -= 25
        
        return y
    
    def _clausula_2(self, emprestimo, y):
        """Cláusula 2 - Taxa de juros"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "SEGUNDA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Taxas de juros")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        periodicidade = "semanais" if getattr(emprestimo, 'periodicidade', 'semanal') == 'semanal' else "mensais"
        texto = f"O empréstimo vence juros a taxa de {emprestimo.taxa_juros}%, sendo as prestações de juros {periodicidade}, sucessivas e contadas em forma de prestações mensais sobre o capital em dívida."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 25
        
        return y
    
    def _clausula_3(self, emprestimo, y):
        """Cláusula 3 - Modo e lugar de reembolso"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "TERCEIRA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Modo e lugar de reembolso")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        meses = int(emprestimo.quantidade_parcelas / 4) if getattr(emprestimo, 'periodicidade', 'semanal') == 'semanal' else emprestimo.quantidade_parcelas
        
        texto = f"1. O mutuário aceita expressamente devolver o crédito dentro de {meses} ({self._numero_por_extenso(meses)}) meses contados a partir da data de desembolso do crédito bem como de acordo com plano de pagamento em anexo ao contrato."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "2. O mutuário compromete-se ainda, a efectuar os reembolsos do crédito nas contas em anexo no plano de pagamento, apresentando o comprovativo do reembolso junto à sede do operador para que lhe seja passado o recibo que confirma a recepção do valor pelo operador."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 25
        
        return y
    
    def _clausula_4(self, y):
        """Cláusula 4 - Vencimento imediato"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "QUARTA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Vencimento imediato")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        texto = "Pode ser considerado imediatamente vencido o presente contrato exigindo-se de imediatamente, o pagamento de todo o valor de capital e juros, ainda em dívida, bem como todos os outros encargos devidos pelo mutuário a operadora de crédito por força deste empréstimo em qualquer dos casos seguintes:"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "1. Por falta de pagamento pontual de qualquer das prestações acordadas no plano de pagamento."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "2. Por infracção de qualquer das cláusulas estabelecidas no presente contrato de empréstimo."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "3. Omissão de informação bem como a prestação de informação falsa."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 25
        
        return y
    
    def _clausula_5(self, emprestimo, y):
        """Cláusula 5 - Garantias do mutuário"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "QUINTA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Garantias do mutuário")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        empresa = emprestimo.cliente.usuario.empresa
        nome_empresa = empresa.nome if empresa else "Operadora de Microcrédito"
        
        texto = f"1. Para assegurar o reembolso do capital, juros e de mais encargos inerentes ao empréstimo o mutuário constitui garantia para empréstimo recebido a favor da {nome_empresa}, no valor total de 54.000,00 MZN que ficarão na posse do mutuário. Fazem parte integrante das garantias os seguintes bens:"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        # Tabela de garantias
        self.c.setFont(self.font_name, 9)
        self.c.drawString(self.margem_esquerda, y, "Descrição")
        self.c.drawString(self.margem_esquerda + 350, y, "Montante")
        y -= 12
        self.c.line(self.margem_esquerda, y + 4, self.margem_esquerda + 450, y + 4)
        
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
            self.c.drawString(self.margem_esquerda, y, desc)
            self.c.drawString(self.margem_esquerda + 350, y, valor)
            y -= 12
        
        y -= 10
        texto = "2. As garantias descritas no número anterior poderão ser usadas em futuros créditos sendo o seu montante actualizado."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 25
        
        return y
    
    def _clausula_7_avalista(self, emprestimo, y):
        """Cláusula 7 - Avalista"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "SÉTIMA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Avalista")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        avalista = getattr(emprestimo, 'avalista', None)
        
        if avalista:
            texto = f"O avalista do mutuário {avalista.nome}, natural de {getattr(avalista, 'naturalidade', 'Nampula')}, residente na Cidade de {getattr(avalista, 'residencia', 'Nampula-Muatala')}, portador de BI nr {getattr(avalista, 'numero_documento', '0301007410667B')}, emitido aos {getattr(avalista, 'data_emissao', '15/06/2022')} na cidade de {getattr(avalista, 'local_emissao', 'Nampula')}, compromete-se solidariamente e ilimitada a assumir a responsabilidade que o mutuário tenha contraído com operador caso o mutuário sofra algum impedimento de qualquer natureza que lhe impossibilite de pagar o empréstimo na sua totalidade ou o saldo vigente da dívida com todos os encargos correspondentes. fazem parte dos bens os seguintes:"
        else:
            texto = "O avalista do mutuário [Nome do Avalista], natural de Nampula, residente na Cidade de Nampula-Muatala, portador de BI nr [Número do BI], emitido aos [Data] na cidade de Nampula, compromete-se solidariamente e ilimitada a assumir a responsabilidade que o mutuário tenha contraído com operador caso o mutuário sofra algum impedimento de qualquer natureza que lhe impossibilite de pagar o empréstimo na sua totalidade ou o saldo vigente da dívida com todos os encargos correspondentes. fazem parte dos bens os seguintes:"
        
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        # Tabela de bens do avalista
        self.c.setFont(self.font_name, 9)
        self.c.drawString(self.margem_esquerda, y, "Descrição")
        self.c.drawString(self.margem_esquerda + 350, y, "Montante")
        y -= 12
        self.c.line(self.margem_esquerda, y + 4, self.margem_esquerda + 450, y + 4)
        
        bens = [
            ("Congelador Super Star", "5.000,00 MZN"),
            ("1 TV 21p", "2.000,00 MZN"),
            ("TOTAL", "7.000,00 MZN")
        ]
        
        for desc, valor in bens:
            self.c.drawString(self.margem_esquerda, y, desc)
            self.c.drawString(self.margem_esquerda + 350, y, valor)
            y -= 12
        
        y -= 15
        
        return y
    
    def _clausula_7_arresto(self, y):
        """Cláusula 7 - Arresto e venda dos bens"""
        self.c.setFont(self.font_name, 10)
        texto = "1. O presente penhor pode ser executado logo que, vencida qualquer obrigação que sirva de garantia, verifique mora no ser cumprimento ou ainda quando qualquer um dos bens dado em penhor seja alienado, onerado penhorado, ou objecto de qualquer outra forma apreenção judicial."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "2. O operador fica desde já autorizado caso ocorra qualquer uma das situações previstas no número anterior a proceder a venda extrajudicial dos empenhados a quem melhor intender pelo preço e de mais condições que tenha por convenientes sem dependência a qualquer normalidade cujo fim e reembolsar-se das quantias em dívidas."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 25
        
        return y
    
    def _clausula_8(self, y):
        """Cláusula 8 - Sanções"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "OITAVA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Sanções")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        texto = "1. Caso se verifique falta de pagamento, pontual das prestações do capital e juros, o mutuário aceita e autoriza o operador a aplicação comulativas das seguintes sanções:"
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "2. Pagamento das taxas de juros moratórios diários corresponde a 2% sobre o capital e juros das prestações em atrasos, incluindo os gastos provocados pelas acções de cobranças administrativas legais."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "3. Tomada de imediato dos bens dados mesmo na sua ausência, mediante notificação escrita entregue a qualquer pessoa de maior idade que esteja a residir no local dos bens, bem como avalista familiar autoridade local ou testemunhas idôneas para o efeito."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 25
        
        return y
    
    def _clausula_9(self, y):
        """Cláusula 9 - Lei de foro"""
        self.c.setFont(self.font_name, 12)
        self.c.drawString(self.margem_esquerda, y, "NONA")
        y -= 18
        self.c.setFont(self.font_name, 11)
        self.c.drawString(self.margem_esquerda, y, "Lei de foro")
        y -= 18
        self.c.setFont(self.font_name, 10)
        
        texto = "1. Quaisquer diferendos relacionados com o presente contrato serão resolvidos amigavelmente pelas partes."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 15
        
        texto = "2. Caso as partes não consigam resolver os diferendos nos termos do número anterior, serão exclusivamente competentes o tribunal judicial da cidade de Nampula com renúncia expressa a outros tribunais."
        self._wrap_text(texto, self.margem_esquerda, y, 15)
        y -= 30
        
        return y
    
    def _assinaturas(self, emprestimo, y):
        """Espaço para assinaturas"""
        self.c.setFont(self.font_name, 10)
        self.c.drawString(self.margem_esquerda, y, "Assinatura do mutuário")
        self.c.drawString(self.margem_esquerda + 350, y, "Assinatura do avalista")
        y -= 30
        self.c.line(self.margem_esquerda, y, self.margem_esquerda + 150, y)
        self.c.line(self.margem_esquerda + 350, y, self.margem_esquerda + 500, y)
        y -= 20
        
        # Nome da operadora
        empresa = emprestimo.cliente.usuario.empresa
        nome_operadora = empresa.nome if empresa else "Operadora de Microcrédito"
        self.c.drawString(self.margem_esquerda, y, nome_operadora)
        y -= 20
        
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
        
        self.c.drawString(self.margem_esquerda, y, f"Nampula, {data_atual}")
    
    def _wrap_text(self, text, x, y, line_height):
        """Quebra texto em múltiplas linhas se necessário"""
        max_width = 450  # Aproximadamente 15cm
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)
            if self.c.stringWidth(line_text, self.font_name, 10) > max_width:
                current_line.pop()
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        for i, line in enumerate(lines):
            self.c.drawString(x, y - (i * line_height), line)
        
        return len(lines) * line_height
    
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