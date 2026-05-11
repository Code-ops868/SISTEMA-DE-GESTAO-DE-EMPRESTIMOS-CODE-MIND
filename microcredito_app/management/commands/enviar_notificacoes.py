from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from microcredito_app.models import Empresa, Parcela, Notificacao

class Command(BaseCommand):
    help = 'Gera notificações internas para o sistema'
    
    def handle(self, *args, **options):
        hoje = date.today()
        self.stdout.write(f'🟢 Gerando notificações internas - {hoje}')
        
        empresas = Empresa.objects.filter(status='ativa')
        self.stdout.write(f'📊 Empresas encontradas: {empresas.count()}')
        
        for empresa in empresas:
            self.stdout.write(f'\n📌 Processando empresa: {empresa.nome} (ID: {empresa.id})')
            
            # ============================================
            # 1. NOTIFICAÇÕES DE VENCIMENTO
            # ============================================
            dias_antecedencia = 5
            data_limite = hoje + timedelta(days=dias_antecedencia)
            
            parcelas_proximas = Parcela.objects.filter(
                emprestimo__usuario__empresa=empresa,
                status='pendente',
                data_vencimento__gte=hoje,
                data_vencimento__lte=data_limite
            ).select_related('emprestimo__cliente')
            
            self.stdout.write(f'   📋 Parcelas a vencer: {parcelas_proximas.count()}')
            
            for parcela in parcelas_proximas:
                dias_restantes = (parcela.data_vencimento - hoje).days
                cliente = parcela.emprestimo.cliente
                
                if not cliente:
                    continue
                
                # Verificar se já notificou hoje
                ja_notificado = Notificacao.objects.filter(
                    parcela=parcela,
                    tipo='vencimento',
                    data_envio__date=hoje
                ).exists()
                
                if not ja_notificado:
                    mensagem = f"🔔 Lembrete: Parcela {parcela.numero} vence em {dias_restantes} dias. Valor: MT {parcela.valor:.2f}"
                    
                    Notificacao.objects.create(
                        empresa=empresa,
                        cliente=cliente,
                        parcela=parcela,
                        tipo='vencimento',
                        destinatario=cliente.telefone or '',
                        mensagem=mensagem,
                        status='pendente'
                    )
                    self.stdout.write(f"      ✅ Notificação de vencimento para {cliente.nome}")
            
            # ============================================
            # 2. NOTIFICAÇÕES DE ATRASO
            # ============================================
            parcelas_atrasadas = Parcela.objects.filter(
                emprestimo__usuario__empresa=empresa,
                status='pendente',
                data_vencimento__lt=hoje
            ).select_related('emprestimo__cliente')
            
            self.stdout.write(f'   ⚠️ Parcelas em atraso: {parcelas_atrasadas.count()}')
            
            for parcela in parcelas_atrasadas:
                dias_atraso = (hoje - parcela.data_vencimento).days
                cliente = parcela.emprestimo.cliente
                
                if not cliente:
                    continue
                
                # Verificar se já existe notificação para esta parcela
                ja_notificado = Notificacao.objects.filter(
                    parcela=parcela,
                    tipo='atraso'
                ).exists()
                
                if not ja_notificado:
                    multa = parcela.valor * Decimal('0.02')
                    juros = parcela.valor * Decimal('0.00033') * dias_atraso
                    valor_total = parcela.valor + multa + juros
                    
                    mensagem = f"⚠️ ALERTA: Parcela {parcela.numero} está atrasada há {dias_atraso} dias. Total com juros: MT {valor_total:.2f}"
                    
                    Notificacao.objects.create(
                        empresa=empresa,
                        cliente=cliente,
                        parcela=parcela,
                        tipo='atraso',
                        destinatario=cliente.telefone or '',
                        mensagem=mensagem,
                        status='pendente'
                    )
                    self.stdout.write(f"      ⚠️ Notificação de atraso para {cliente.nome}")
        
        self.stdout.write(self.style.SUCCESS('\n✅ Notificações geradas com sucesso!'))