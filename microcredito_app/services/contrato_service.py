# microcredito_app/services/contrato_service.py

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white, gray
import os
import platform

class ContratoService:
    """Serviço para gerar contrato de empréstimo em PDF"""
    
    def __init__(self):
        # Usar fontes do sistema
        self.font_name = self._get_system_font()
    
    def _get_system_font(self):
        """
        Detecta e usa fontes do sistema para suporte a acentos
        """
        sistema = platform.system()
        
        # Mapeamento de fontes por sistema operacional
        fontes = {
            'Windows': [
                'Arial',           # Windows
                'Times New Roman',
                'Calibri',
            ],
            'Darwin': [  # macOS
                'Helvetica',
                'Arial',
                'Times-Roman',
            ],
            'Linux': [
                'DejaVu-Sans',
                'Liberation-Sans',
                'Nimbus-Roman',
                'Helvetica',
            ]
        }
        
        # Tenta registrar fontes do sistema
        for nome_fonte in fontes.get(sistema, ['Helvetica']):
            try:
                # Tenta usar a fonte diretamente (já registrada no sistema)
                pdfmetrics.getFont(nome_fonte)
                return nome_fonte
            except:
                pass
        
        # Fallback: usa Helvetica (padrão do reportlab)
        return 'Helvetica'
    
    def gerar_contrato(self, emprestimo):
        """
        Gera o PDF do contrato a partir dos dados do empréstimo
        
        Args:
            emprestimo: Objeto do empréstimo com todas as informações
        
        Returns:
            bytes: Conteúdo do PDF
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Margens
        margem_esquerda = 2 * cm
        margem_superior = height - 2 * cm
        largura_util = width - 2 * margem_esquerda
        
        # ============================================
        # TÍTULO
        # ============================================
        c.setFont(self.font_name, 16)
        c.drawCentredString(width / 2, margem_superior, "CONTRATO DE EMPRÉSTIMO")
        
        # Linha abaixo do título
        c.line(margem_esquerda, margem_superior - 10, width - margem_esquerda, margem_superior - 10)
        
        # ============================================
        # DADOS DA EMPRESA (OPERADORA)
        # ============================================
        y = margem_superior - 30
        c.setFont(self.font_name, 10)
        
        empresa = emprestimo.cliente.usuario.empresa
        if empresa:
            c.drawString(margem_esquerda, y, f"Entre a {empresa.nome}, com sede na cidade de {empresa.endereco or 'Nampula'},")
            y -= 15
            c.drawString(margem_esquerda, y, f"representado neste pela Senhora(a) {emprestimo.cliente.usuario.get_full_name()} na qualidade de administradora,")
        else:
            c.drawString(margem_esquerda, y, "Entre a Operadora de Microcrédito, com sede na cidade de Nampula,")
            y -= 15
            c.drawString(margem_esquerda, y, "representado neste pela Senhora(a) [Nome do Representante] na qualidade de administradora,")
        
        y -= 20
        
        # ============================================
        # DADOS DO CLIENTE (MUTUÁRIO)
        # ============================================
        cliente = emprestimo.cliente
        c.drawString(margem_esquerda, y, "E")
        y -= 20
        
        c.drawString(margem_esquerda, y, f"{cliente.nome}, {cliente.estado_civil or 'solteiro(a)'}, de Nacionalidade Moçambicana,")
        y -= 15
        c.drawString(margem_esquerda, y, f"residente em {cliente.endereco or 'Nampula, bairro de [Bairro]'},")
        y -= 15
        c.drawString(margem_esquerda, y, f"celular no {cliente.telefone},")
        y -= 15
        
        # Documento de identificação
        doc_tipo = "BI"
        doc_numero = cliente.bi_passaporte or "[Número do Documento]"
        if cliente.bi_passaporte:
            if len(cliente.bi_passaporte) == 13:  # BI (12 dígitos + letra)
                doc_tipo = "BI"
            elif len(cliente.bi_passaporte) == 9:  # DIRE
                doc_tipo = "DIRE"
            else:
                doc_tipo = "Passaporte"
        
        c.drawString(margem_esquerda, y, f"Portador do {doc_tipo} no {doc_numero},")
        y -= 15
        c.drawString(margem_esquerda, y, f"emitido aos {cliente.data_emissao_documento.strftime('%d-%m-%Y') if cliente.data_emissao_documento else '[Data de Emissão]'} pelo arquivo de identificação de Nampula,")
        y -= 15
        c.drawString(margem_esquerda, y, f"valido ate {cliente.data_validade_documento.strftime('%d-%m-%Y') if cliente.data_validade_documento else '[Data de Validade]'}")
        y -= 20
        
        c.drawString(margem_esquerda, y, "doravante é designado mutuário.")
        y -= 25
        
        # ============================================
        # INTRODUÇÃO
        # ============================================
        c.drawString(margem_esquerda, y, "É celebrado o presente contrato de empréstimo, que se regerá pelas cláusulas e termos seguintes:")
        y -= 25
        
        # ============================================
        # CLÁUSULA 1 - VALOR
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "PRIMEIRA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Valor de empréstimo")
        y -= 18
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, f"Pelo presente, concede-se ao mutuário o valor de {emprestimo.valor:,.2f} MZN")
        y -= 15
        c.drawString(margem_esquerda, y, f"({self._valor_por_extenso(emprestimo.valor)}) a ser pago em {emprestimo.quantidade_parcelas} (")
        c.drawString(margem_esquerda + 380, y, f"{self._numero_por_extenso(emprestimo.quantidade_parcelas)}) prestações")
        y -= 15
        
        periodicidade = "semanais" if emprestimo.periodicidade == 'semanal' else "mensais"
        c.drawString(margem_esquerda, y, f"{periodicidade}")
        y -= 25
        
        # ============================================
        # CLÁUSULA 2 - JUROS
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "SEGUNDA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Taxas de juros")
        y -= 18
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, f"O empréstimo vence juros a taxa de {emprestimo.taxa_juros}%, sendo as prestações de juros {periodicidade},")
        y -= 15
        c.drawString(margem_esquerda, y, "sucessivas e contadas em forma de prestações mensais sobre o capital em dívida.")
        y -= 25
        
        # ============================================
        # CLÁUSULA 3 - REEMBOLSO
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "TERCEIRA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Modo e lugar de reembolso")
        y -= 18
        c.setFont(self.font_name, 10)
        
        meses = int(emprestimo.quantidade_parcelas / 4) if emprestimo.periodicidade == 'semanal' else emprestimo.quantidade_parcelas
        c.drawString(margem_esquerda, y, f"1. O mutuário aceita expressamente devolver o crédito dentro de {meses} (")
        c.drawString(margem_esquerda + 360, y, f"{self._numero_por_extenso(meses)}) meses")
        y -= 15
        c.drawString(margem_esquerda, y, f"contados a partir da data de desembolso do crédito bem como de acordo com plano de pagamento")
        y -= 15
        c.drawString(margem_esquerda, y, "em anexo ao contrato.")
        y -= 20
        
        c.drawString(margem_esquerda, y, "2. O mutuário compromete-se ainda, a efectuar os reembolsos do crédito nas contas")
        y -= 15
        c.drawString(margem_esquerda, y, "em anexo no plano de pagamento, apresentando o comprovativo do reembolso junto à")
        y -= 15
        c.drawString(margem_esquerda, y, "sede do operador para que lhe seja passado o recibo que confirma a recepção do")
        y -= 15
        c.drawString(margem_esquerda, y, "valor pelo operador.")
        y -= 25
        
        # ============================================
        # CLÁUSULA 4 - VENCIMENTO IMEDIATO
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "QUARTA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Vencimento imediato")
        y -= 18
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, "Pode ser considerado imediatamente vencido o presente contrato exigindo-se de imediatamente,")
        y -= 15
        c.drawString(margem_esquerda, y, "o pagamento de todo o valor de capital e juros, ainda em dívida, bem como todos os")
        y -= 15
        c.drawString(margem_esquerda, y, "outros encargos devidos pelo mutuário a operadora de crédito por força deste")
        y -= 15
        c.drawString(margem_esquerda, y, "empréstimo em qualquer dos casos seguintes:")
        y -= 15
        c.drawString(margem_esquerda, y, "1. Por falta de pagamento pontual de qualquer das prestações acordadas no plano de")
        y -= 15
        c.drawString(margem_esquerda, y, "pagamento.")
        y -= 15
        c.drawString(margem_esquerda, y, "2. Por infracção de qualquer das cláusulas estabelecidas no presente contrato de")
        y -= 15
        c.drawString(margem_esquerda, y, "empréstimo.")
        y -= 15
        c.drawString(margem_esquerda, y, "3. Omissão de informação bem como a prestação de informação falsa.")
        y -= 25
        
        # ============================================
        # CLÁUSULA 5 - GARANTIAS
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "QUINTA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Garantias do mutuário")
        y -= 18
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, "1. Para assegurar o reembolso do capital, juros e de mais encargos inerentes ao")
        y -= 15
        c.drawString(margem_esquerda, y, "empréstimo o mutuário constitui garantia para empréstimo recebido a favor da")
        y -= 15
        c.drawString(margem_esquerda, y, f"{empresa.nome if empresa else 'Operadora de Microcrédito'},")
        y -= 15
        
        # Tabela de garantias
        if emprestimo.garantias:
            total_garantias = 0
            c.drawString(margem_esquerda, y, f"no valor total de {sum([g['valor'] for g in emprestimo.garantias]):,.2f} MZN")
            y -= 15
            c.drawString(margem_esquerda, y, "que ficarão na posse do mutuário. Fazem parte integrante das garantias os")
            y -= 15
            c.drawString(margem_esquerda, y, "seguintes bens:")
            y -= 15
            
            # Tabela
            c.setFont(self.font_name, 9)
            c.drawString(margem_esquerda, y, "Descrição")
            c.drawString(margem_esquerda + 350, y, "Montante")
            y -= 12
            c.line(margem_esquerda, y + 4, width - margem_esquerda, y + 4)
            
            for garantia in emprestimo.garantias:
                descricao = garantia.get('descricao', '')
                valor = garantia.get('valor', 0)
                c.drawString(margem_esquerda, y, descricao[:40])
                c.drawString(margem_esquerda + 350, y, f"{valor:,.2f} MZN")
                y -= 12
                total_garantias += valor
        else:
            c.drawString(margem_esquerda, y, "no valor total de 54.000,00 MZN que ficarão na posse do mutuário. Fazem parte")
            y -= 15
            c.drawString(margem_esquerda, y, "integrante das garantias os seguintes bens:")
            y -= 15
            c.setFont(self.font_name, 9)
            c.drawString(margem_esquerda, y, "Descrição")
            c.drawString(margem_esquerda + 350, y, "Montante")
            y -= 12
            c.line(margem_esquerda, y + 4, width - margem_esquerda, y + 4)
            
            garantias_default = [
                ("Dois Congeladores", 12000.00),
                ("Arca", 15000.00),
                ("2 Arcas Brancas", 20000.00),
                ("3 Mesas Plásticas", 1500.00),
                ("12 Cadeiras Plásticas", 1500.00),
                ("Fogão a Gás com Botija", 4000.00),
            ]
            total_garantias = 0
            for desc, val in garantias_default:
                c.drawString(margem_esquerda, y, desc)
                c.drawString(margem_esquerda + 350, y, f"{val:,.2f} MZN")
                y -= 12
                total_garantias += val
            
            c.drawString(margem_esquerda, y, "TOTAL")
            c.drawString(margem_esquerda + 350, y, f"{total_garantias:,.2f} MZN")
        
        y -= 20
        
        # ============================================
        # AVALISTA
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "SÉTIMA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Avalista")
        y -= 18
        c.setFont(self.font_name, 10)
        
        if emprestimo.avalista:
            avalista = emprestimo.avalista
            c.drawString(margem_esquerda, y, f"O avalista do mutuário {avalista.nome},")
            y -= 15
            c.drawString(margem_esquerda, y, f"natural de {avalista.naturalidade or 'Nampula'},")
            y -= 15
            c.drawString(margem_esquerda, y, f"residente na Cidade de {avalista.residencia or 'Nampula'},")
            y -= 15
            c.drawString(margem_esquerda, y, f"portador de {avalista.tipo_documento or 'BI'} nr {avalista.numero_documento},")
            y -= 15
            c.drawString(margem_esquerda, y, f"emitido aos {avalista.data_emissao.strftime('%d/%m/%Y') if avalista.data_emissao else '[Data]'} na cidade de {avalista.local_emissao or 'Nampula'},")
            y -= 15
            c.drawString(margem_esquerda, y, "compromete-se solidariamente e ilimitada a assumir a responsabilidade que o")
            y -= 15
            c.drawString(margem_esquerda, y, "mutuário tenha contraído com operador caso o mutuário sofra algum impedimento")
            y -= 15
            c.drawString(margem_esquerda, y, "de qualquer natureza que lhe impossibilite de pagar o empréstimo na sua")
            y -= 15
            c.drawString(margem_esquerda, y, "totalidade ou o saldo vigente da dívida com todos os encargos correspondentes.")
            y -= 15
            c.drawString(margem_esquerda, y, "fazem parte dos bens os seguintes:")
        else:
            c.drawString(margem_esquerda, y, "O avalista do mutuário [Nome do Avalista], natural de Nampula,")
            y -= 15
            c.drawString(margem_esquerda, y, "residente na Cidade de Nampula, portador de BI nr [Número do BI],")
            y -= 15
            c.drawString(margem_esquerda, y, "emitido aos [Data] na cidade de Nampula,")
            y -= 15
            c.drawString(margem_esquerda, y, "compromete-se solidariamente e ilimitada a assumir a responsabilidade que o")
            y -= 15
            c.drawString(margem_esquerda, y, "mutuário tenha contraído com operador caso o mutuário sofra algum impedimento")
            y -= 15
            c.drawString(margem_esquerda, y, "de qualquer natureza que lhe impossibilite de pagar o empréstimo na sua")
            y -= 15
            c.drawString(margem_esquerda, y, "totalidade ou o saldo vigente da dívida com todos os encargos correspondentes.")
            y -= 15
            c.drawString(margem_esquerda, y, "fazem parte dos bens os seguintes:")
        
        y -= 15
        c.setFont(self.font_name, 9)
        c.drawString(margem_esquerda, y, "Descrição")
        c.drawString(margem_esquerda + 350, y, "Montante")
        y -= 12
        c.line(margem_esquerda, y + 4, width - margem_esquerda, y + 4)
        
        if emprestimo.avalista and emprestimo.avalista.bens:
            for bem in emprestimo.avalista.bens:
                c.drawString(margem_esquerda, y, bem.get('descricao', ''))
                c.drawString(margem_esquerda + 350, y, f"{bem.get('valor', 0):,.2f} MZN")
                y -= 12
        else:
            c.drawString(margem_esquerda, y, "Congelador super star")
            c.drawString(margem_esquerda + 350, y, "5.000,00 MZN")
            y -= 12
            c.drawString(margem_esquerda, y, "1 TV 21p")
            c.drawString(margem_esquerda + 350, y, "2.000,00 MZN")
            y -= 12
            c.drawString(margem_esquerda, y, "TOTAL")
            c.drawString(margem_esquerda + 350, y, "7.000,00 MZN")
        
        y -= 25
        
        # ============================================
        # SANÇÕES
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "OITAVA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Sanções")
        y -= 18
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, "1. Caso se verifique falta de pagamento, pontual das prestações do capital e juros,")
        y -= 15
        c.drawString(margem_esquerda, y, "o mutuário aceita e autoriza o operador a aplicação comulativas das seguintes")
        y -= 15
        c.drawString(margem_esquerda, y, "sanções:")
        y -= 15
        c.drawString(margem_esquerda, y, "2. Pagamento das taxas de juros moratórios diários corresponde a 0,1% sobre o")
        y -= 15
        c.drawString(margem_esquerda, y, "capital e juros das prestações em atrasos, incluindo os gastos provocados pelas")
        y -= 15
        c.drawString(margem_esquerda, y, "acções de cobranças administrativas legais.")
        y -= 15
        c.drawString(margem_esquerda, y, "3. Tomada de imediato dos bens dados mesmo na sua ausência, mediante notificação")
        y -= 15
        c.drawString(margem_esquerda, y, "escrita entregue a qualquer pessoa de maior idade que esteja a residir no local")
        y -= 15
        c.drawString(margem_esquerda, y, "dos bens, bem como avalista familiar autoridade local ou testemunhas idôneas")
        y -= 15
        c.drawString(margem_esquerda, y, "para o efeito.")
        y -= 25
        
        # ============================================
        # FORO
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "NONA")
        y -= 18
        c.setFont(self.font_name, 11)
        c.drawString(margem_esquerda, y, "Lei de foro")
        y -= 18
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, "1. Quaisquer diferendos relacionados com o presente contrato serão resolvidos")
        y -= 15
        c.drawString(margem_esquerda, y, "amigavelmente pelas partes.")
        y -= 15
        c.drawString(margem_esquerda, y, "2. Caso as partes não consigam resolver os diferendos nos termos do número")
        y -= 15
        c.drawString(margem_esquerda, y, "anterior, serão exclusivamente competentes o tribunal judicial da cidade de")
        y -= 15
        c.drawString(margem_esquerda, y, "Nampula com renúncia expressa a outros tribunais.")
        y -= 30
        
        # ============================================
        # ASSINATURAS
        # ============================================
        c.setFont(self.font_name, 10)
        c.drawString(margem_esquerda, y, "Assinatura do mutuário")
        c.drawString(margem_esquerda + 350, y, "Assinatura do avalista")
        y -= 30
        c.line(margem_esquerda, y, margem_esquerda + 150, y)
        c.line(margem_esquerda + 350, y, margem_esquerda + 500, y)
        y -= 20
        
        # Nome da operadora
        nome_operadora = empresa.nome if empresa else "Operadora de Microcrédito"
        c.drawString(margem_esquerda, y, nome_operadora)
        
        # Data
        y -= 20
        c.drawString(margem_esquerda, y, f"Nampula, {datetime.now().strftime('%d de %B de %Y')}")
        
        # ============================================
        # FINALIZAR PDF
        # ============================================
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _valor_por_extenso(self, valor):
        """Converte valor numérico para extenso (simplificado)"""
        try:
            inteiro = int(valor)
            return f"{inteiro} mil meticais"
        except:
            return "valor em meticais"
    
    def _numero_por_extenso(self, numero):
        """Converte número para extenso (simplificado)"""
        numeros = {
            1: 'uma', 2: 'duas', 3: 'três', 4: 'quatro', 5: 'cinco',
            6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove', 10: 'dez',
            11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze', 15: 'quinze',
            16: 'dezasseis', 17: 'dezassete', 18: 'dezoito', 19: 'dezanove', 20: 'vinte',
            30: 'trinta', 40: 'quarenta', 50: 'cinquenta', 60: 'sessenta',
            70: 'setenta', 80: 'oitenta', 90: 'noventa', 100: 'cem'
        }
        if numero <= 20:
            return numeros.get(numero, str(numero))
        elif numero < 100:
            dezena = (numero // 10) * 10
            unidade = numero % 10
            if unidade == 0:
                return numeros.get(dezena, str(numero))
            return f"{numeros.get(dezena, '')} e {numeros.get(unidade, '')}"
        return str(numero)