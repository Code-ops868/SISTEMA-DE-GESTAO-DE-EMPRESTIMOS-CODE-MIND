from django.core.management.base import BaseCommand
from microcredito_app.models import Plano  # ← NOME CORRETO

class Command(BaseCommand):
    help = 'Cria os planos de assinatura no banco de dados'

    def handle(self, *args, **options):
        planos = [
            {'nome': 'mensal', 'descricao': 'Plano Mensal', 'valor': 1000, 'duracao_dias': 30},
            {'nome': 'trimestral', 'descricao': 'Plano Trimestral', 'valor': 2250, 'duracao_dias': 90},
            {'nome': 'anual', 'descricao': 'Plano Anual', 'valor': 8000, 'duracao_dias': 365},
        ]
        
        for plano_data in planos:
            plano, created = Plano.objects.get_or_create(
                nome=plano_data['nome'],
                defaults={
                    'descricao': plano_data['descricao'],
                    'valor': plano_data['valor'],
                    'duracao_dias': plano_data['duracao_dias'],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Plano {plano.get_nome_display()} criado!'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Plano {plano.get_nome_display()} já existe.'))
        
        self.stdout.write(self.style.SUCCESS('🎉 Todos os planos foram processados!'))