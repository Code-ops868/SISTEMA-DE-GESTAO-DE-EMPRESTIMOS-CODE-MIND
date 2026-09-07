# microcredito_app/services/contrato_service.py

import io
import os
from datetime import datetime
from docxtpl import DocxTemplate
from django.conf import settings

class ContratoService:
    """Serviço para gerar contrato de empréstimo usando template DOCX"""
    
    def __init__(self):
        self.template_path = self._get_template_path()
    
    def _get_template_path(self):
        """Retorna o caminho do template do contrato"""
        base_dir = settings.BASE_DIR
        template_path = os.path.join(
            base_dir, 
            'microcredito_app', 
            'templates', 
            'contrato', 
            'contrato.docx'  # ← Nome corrigido
        )
        return template_path
    
    def _numero_por_extenso(self, numero):
        """Converte número para extenso"""
        numeros = {
            1: 'uma', 2: 'duas', 3: 'três', 4: 'quatro', 5: 'cinco',
            6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove', 10: 'dez',
            11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze', 15: 'quinze',
            16: 'dezasseis', 17: 'dezassete', 18: 'dezoito', 19: 'dezanove', 20: 'vinte',
            21: 'vinte e uma', 22: 'vinte e duas', 23: 'vinte e três', 24: 'vinte e quatro',
            25: 'vinte e cinco', 26: 'vinte e seis', 27: 'vinte e sete', 28: 'vinte e oito',
            29: 'vinte e nove', 30: 'trinta', 40: 'quarenta', 50: 'cinquenta',
            60: 'sessenta', 70: 'setenta', 80: 'oitenta', 90: 'noventa', 100: 'cem'
        }
        return numeros.get(numero, str(numero))
    
    def _valor_por_extenso(self, valor):
        """Converte valor monetário para extenso"""
        try:
            inteiro = int(valor)
            if inteiro >= 1000:
                return f"{inteiro // 1000} mil meticais"
            return f"{inteiro} meticais"
        except:
            return "valor em meticais"
    
    def _get_data_formatada(self, data):
        """Formata data para o formato dd/mm/yyyy"""
        if not data:
            return "____/____/______"
        return data.strftime("%d/%m/%Y")
    
    def _get_garantias_padrao(self):
        """Retorna lista de garantias padrão do contrato"""
        return [
            {'descricao': 'Dois Congeladores', 'montante': '12.000,00'},
            {'descricao': 'Arca', 'montante': '15.000,00'},
            {'descricao': '2 Arcas Brancas', 'montante': '20.000,00'},
            {'descricao': '3 Mesas Plásticas', 'montante': '1.500,00'},
            {'descricao': '12 Cadeiras Plásticas', 'montante': '1.500,00'},
            {'descricao': 'Fogão a Gás com Botija', 'montante': '4.000,00'},
        ]
    
    def _get_garantias_avalista_padrao(self):
        """Retorna lista de garantias do avalista padrão"""
        return [
            {'descricao': 'Congelador Super Star', 'montante': '5.000,00'},
            {'descricao': '1 TV 21p', 'montante': '2.000,00'},
        ]
    
    def gerar_contrato(self, emprestimo):
        """
        Gera o contrato preenchendo o template DOCX
        """
        cliente = emprestimo.cliente
        usuario = cliente.usuario
        empresa = usuario.empresa if hasattr(usuario, 'empresa') else None
        
        # Calcular prazo de reembolso (meses)
        periodicidade = getattr(emprestimo, 'periodicidade', 'semanal')
        if periodicidade == 'semanal':
            prazo_meses = int(emprestimo.quantidade_parcelas / 4)
            periodicidade_prestacoes = 'semanais'
        else:
            prazo_meses = emprestimo.quantidade_parcelas
            periodicidade_prestacoes = 'mensais'
        
        # Dados da empresa
        if empresa:
            operadora_nome = empresa.nome
            operadora_cidade = "Nampula"
            operadora_endereco = empresa.endereco or "Rua de Teté"
            administradora_nome = usuario.get_full_name() or usuario.username
        else:
            operadora_nome = "Operadora de Microcrédito"
            operadora_cidade = "Nampula"
            operadora_endereco = "Rua de Teté"
            administradora_nome = "Senhor(a) Administrador(a)"
        
        # Dados do mutuário
        mutuario_estado_civil = getattr(cliente, 'estado_civil', 'solteiro(a)')
        mutuario_nacionalidade = "Moçambicana"
        mutuario_residencia = cliente.endereco or "Nampula, bairro de [Bairro]"
        mutuario_celular = cliente.telefone
        
        # Documento do mutuário
        mutuario_dire = cliente.bi_passaporte or "[Número do Documento]"
        mutuario_dire_emissao = self._get_data_formatada(cliente.data_emissao_documento) if cliente.data_emissao_documento else "[Data de Emissão]"
        mutuario_dire_local = "Nampula"
        mutuario_dire_validade = self._get_data_formatada(cliente.data_validade_documento) if cliente.data_validade_documento else "[Data de Validade]"
        
        # Dados do empréstimo
        valor_emprestimo = f"{emprestimo.valor:,.2f}".replace(',', '.')
        valor_emprestimo_extenso = self._valor_por_extenso(emprestimo.valor)
        numero_prestacoes = emprestimo.quantidade_parcelas
        numero_prestacoes_extenso = self._numero_por_extenso(numero_prestacoes)
        taxa_juros = emprestimo.taxa_juros
        
        # Dados de reembolso
        prazo_reembolso = prazo_meses
        prazo_reembolso_extenso = self._numero_por_extenso(prazo_meses)
        
        # Garantias
        garantias = self._get_garantias_padrao()
        total_garantias = 0
        for g in garantias:
            total_garantias += float(g['montante'].replace('.', '').replace(',', '.'))
        
        # Dados do avalista
        avalista = getattr(emprestimo, 'avalista', None)
        if avalista:
            avalista_nome = avalista.nome
            avalista_naturalidade = getattr(avalista, 'naturalidade', 'Nampula')
            avalista_residencia = getattr(avalista, 'residencia', 'Nampula-Muatala')
            avalista_bi = getattr(avalista, 'numero_documento', '0301007410667B')
            avalista_bi_emissao = getattr(avalista, 'data_emissao', '15/06/2022')
            avalista_bi_local = getattr(avalista, 'local_emissao', 'Nampula')
            garantias_avalista = getattr(avalista, 'bens', self._get_garantias_avalista_padrao())
        else:
            avalista_nome = "[Nome do Avalista]"
            avalista_naturalidade = "Nampula"
            avalista_residencia = "Nampula-Muatala"
            avalista_bi = "[Número do BI]"
            avalista_bi_emissao = "[Data]"
            avalista_bi_local = "Nampula"
            garantias_avalista = self._get_garantias_avalista_padrao()
        
        # Total das garantias do avalista
        total_garantias_avalista = 0
        for g in garantias_avalista:
            total_garantias_avalista += float(g['montante'].replace('.', '').replace(',', '.'))
        
        # Taxa de juros mora
        taxa_juros_mora = 2.0
        
        # Foro
        foro_cidade = "Nampula"
        
        # Data do contrato
        contrato_data = datetime.now().strftime("%d de %B de %Y")
        meses = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }
        for en, pt in meses.items():
            contrato_data = contrato_data.replace(en, pt)
        
        # Montar contexto do template
        context = {
            'operadora_nome': operadora_nome,
            'operadora_cidade': operadora_cidade,
            'operadora_endereco': operadora_endereco,
            'administradora_nome': administradora_nome,
            'mutuario_nome': cliente.nome,
            'mutuario_estado_civil': mutuario_estado_civil,
            'mutuario_nacionalidade': mutuario_nacionalidade,
            'mutuario_residencia': mutuario_residencia,
            'mutuario_celular': mutuario_celular,
            'mutuario_dire': mutuario_dire,
            'mutuario_dire_emissao': mutuario_dire_emissao,
            'mutuario_dire_local': mutuario_dire_local,
            'mutuario_dire_validade': mutuario_dire_validade,
            'valor_emprestimo': valor_emprestimo,
            'valor_emprestimo_extenso': valor_emprestimo_extenso,
            'numero_prestacoes': numero_prestacoes,
            'numero_prestacoes_extenso': numero_prestacoes_extenso,
            'periodicidade_prestacoes': periodicidade_prestacoes,
            'taxa_juros': taxa_juros,
            'prazo_reembolso': prazo_reembolso,
            'prazo_reembolso_extenso': prazo_reembolso_extenso,
            'garantias': garantias,
            'valor_total_garantias_mutuario': f"{total_garantias:,.2f}".replace(',', '.'),
            'avalista_nome': avalista_nome,
            'avalista_naturalidade': avalista_naturalidade,
            'avalista_residencia': avalista_residencia,
            'avalista_bi': avalista_bi,
            'avalista_bi_emissao': avalista_bi_emissao,
            'avalista_bi_local': avalista_bi_local,
            'garantias_avalista': garantias_avalista,
            'valor_total_garantias_avalista': f"{total_garantias_avalista:,.2f}".replace(',', '.'),
            'taxa_juros_mora': taxa_juros_mora,
            'foro_cidade': foro_cidade,
            'contrato_cidade': "Nampula",
            'contrato_data': contrato_data,
        }
        
        # Carregar e preencher o template
        try:
            doc = DocxTemplate(self.template_path)
            doc.render(context)
            
            # Salvar em memória
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            return buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Erro ao gerar contrato: {str(e)}")