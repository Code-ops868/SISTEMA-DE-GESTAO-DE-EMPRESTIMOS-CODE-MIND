# microcredito_app/services/contrato_service.py

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

class ContratoService:
    """Serviço para gerar contrato de empréstimo em PDF"""
    
    def __init__(self):
        self.font_name = 'Helvetica'
    
    def gerar_contrato(self, emprestimo):
        """
        Gera o PDF do contrato a partir dos dados do empréstimo
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Margens
        margem_esquerda = 2 * cm
        y = height - 2 * cm
        
        # ============================================
        # TÍTULO
        # ============================================
        c.setFont(self.font_name, 16)
        c.drawCentredString(width / 2, y, "CONTRATO DE EMPRÉSTIMO")
        y -= 20
        c.line(margem_esquerda, y, width - margem_esquerda, y)
        y -= 30
        
        # ============================================
        # DADOS DO CLIENTE
        # ============================================
        c.setFont(self.font_name, 10)
        cliente = emprestimo.cliente
        
        c.drawString(margem_esquerda, y, f"Cliente: {cliente.nome}")
        y -= 20
        c.drawString(margem_esquerda, y, f"Telefone: {cliente.telefone}")
        y -= 20
        c.drawString(margem_esquerda, y, f"Documento: {cliente.bi_passaporte or 'Nao informado'}")
        y -= 20
        
        if cliente.endereco:
            c.drawString(margem_esquerda, y, f"Endereço: {cliente.endereco}")
            y -= 20
        
        y -= 20
        
        # ============================================
        # DADOS DO EMPRÉSTIMO
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "DADOS DO EMPRÉSTIMO")
        y -= 20
        c.setFont(self.font_name, 10)
        
        c.drawString(margem_esquerda, y, f"Valor do Empréstimo: {emprestimo.valor:,.2f} MZN")
        y -= 20
        c.drawString(margem_esquerda, y, f"Taxa de Juros: {emprestimo.taxa_juros}%")
        y -= 20
        c.drawString(margem_esquerda, y, f"Número de Parcelas: {emprestimo.quantidade_parcelas}")
        y -= 20
        c.drawString(margem_esquerda, y, f"Valor da Parcela: {emprestimo.valor_parcela:,.2f} MZN")
        y -= 20
        c.drawString(margem_esquerda, y, f"Data do Contrato: {emprestimo.data_contrato.strftime('%d/%m/%Y')}")
        y -= 20
        
        if emprestimo.data_primeiro_vencimento:
            c.drawString(margem_esquerda, y, f"Primeiro Vencimento: {emprestimo.data_primeiro_vencimento.strftime('%d/%m/%Y')}")
            y -= 20
        
        # Status
        status_text = {
            'ativo': 'Ativo',
            'pago': 'Pago',
            'atrasado': 'Atrasado',
            'cancelado': 'Cancelado'
        }.get(emprestimo.status, emprestimo.status)
        c.drawString(margem_esquerda, y, f"Status: {status_text}")
        y -= 30
        
        # ============================================
        # CLÁUSULAS
        # ============================================
        c.setFont(self.font_name, 12)
        c.drawString(margem_esquerda, y, "CLÁUSULAS DO CONTRATO")
        y -= 20
        c.setFont(self.font_name, 10)
        
        # Cláusula 1
        c.drawString(margem_esquerda, y, "1. O mutuário recebeu o valor acima descrito e compromete-se a devolvê-lo")
        y -= 15
        c.drawString(margem_esquerda, y, f"   em {emprestimo.quantidade_parcelas} parcelas de {emprestimo.valor_parcela:,.2f} MZN cada.")
        y -= 20
        
        # Cláusula 2
        c.drawString(margem_esquerda, y, "2. O não pagamento de qualquer parcela implica na cobrança de juros de mora")
        y -= 15
        c.drawString(margem_esquerda, y, "   e multa conforme previsto em lei.")
        y -= 20
        
        # Cláusula 3
        c.drawString(margem_esquerda, y, "3. O mutuário declara que as informações prestadas são verdadeiras e")
        y -= 15
        c.drawString(margem_esquerda, y, "   compromete-se a comunicar qualquer alteração dos seus dados.")
        y -= 25
        
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
        
        # Data
        c.drawString(margem_esquerda, y, f"Nampula, {datetime.now().strftime('%d de %B de %Y')}")
        
        # ============================================
        # FINALIZAR PDF
        # ============================================
        c.save()
        buffer.seek(0)
        return buffer.getvalue()