from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Empresa, Notificacao
from django.contrib.auth.models import User

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Empresa, Notificacao
from django.contrib.auth.models import User


# ============================================
# SIGNAL 1: Garantir que TODO superusuário tenha empresa (incluindo existentes)
# ============================================
@receiver(post_save, sender=User)
def garantir_empresa_para_superuser(sender, instance, **kwargs):
    """Cria empresa automaticamente para qualquer superusuário (admin) - inclusive os existentes"""
    if instance.is_superuser:
        empresa, criada = Empresa.objects.get_or_create(
            user=instance,
            defaults={
                'nome': f"Empresa {instance.username}",
                'status': 'ativa'
            }
        )
        if criada:
            print(f"✅ Empresa criada automaticamente para superusuário {instance.username}")


# ============================================
# SIGNAL 2: Notificar admin sobre novas empresas e enviar boas-vindas
# ============================================
@receiver(post_save, sender=Empresa)
def notificar_nova_empresa(sender, instance, created, **kwargs):
    """Envia notificações quando uma nova empresa é cadastrada"""
    if created:
        # Buscar o superusuário (admin)
        admin = User.objects.filter(is_superuser=True).first()
        
        # Garantir que o admin tem empresa (criar se não tiver)
        if admin and not hasattr(admin, 'empresa'):
            Empresa.objects.get_or_create(
                user=admin,
                defaults={'nome': f"Empresa {admin.username}", 'status': 'ativa'}
            )
            # Recarregar o admin para ter o atributo empresa
            admin.refresh_from_db()
        
        # 1. Notificar o ADMIN
        if admin and hasattr(admin, 'empresa'):
            Notificacao.objects.create(
                empresa=admin.empresa,
                tipo='info',
                status='pendente',
                mensagem=f'🏢 Nova empresa cadastrada: {instance.nome}',
                destinatario=admin.email or ''
            )
            print(f"✅ Admin notificado: Nova empresa {instance.nome}")
        
        # 2. Notificar a PRÓPRIA EMPRESA (boas-vindas)
        Notificacao.objects.create(
            empresa=instance,
            tipo='info',
            status='pendente',
            mensagem=f'✅ Bem-vindo {instance.nome}! Seu cadastro foi realizado com sucesso na CODE-MIND.',
            destinatario=instance.user.email or ''
        )
        print(f"✅ Boas-vindas enviada para {instance.nome}")


# ============================================
# SIGNAL 3: Criar administrador da empresa automaticamente (NOVO)
# ============================================
@receiver(post_save, sender=Empresa)
def criar_admin_empresa(sender, instance, created, **kwargs):
    """Cria um funcionário com cargo admin_empresa quando uma nova empresa é criada"""
    if created:
        from .models import Funcionario
        Funcionario.objects.create(
            usuario=instance.user,
            empresa=instance,
            cargo='admin_empresa',
            pode_baixar_emprestimos=True,
            pode_regularizar_parcelas=True,
            pode_configurar_empresa=True,
            ativo=True
        )
        print(f"✅ Administrador da empresa {instance.nome} criado automaticamente")


# ============================================
# EXECUÇÃO ÚNICA: Garantir que admin existente tenha empresa (roda na inicialização)
# ============================================
from django.apps import apps
if apps.ready:
    for user in User.objects.filter(is_superuser=True):
        empresa, criada = Empresa.objects.get_or_create(
            user=user,
            defaults={'nome': f"Empresa {user.username}", 'status': 'ativa'}
        )
        if criada:
            print(f"✅ Empresa criada para admin existente: {user.username}")
    
    # NOVO: Garantir que empresas existentes tenham admin
    from .models import Funcionario
    for empresa in Empresa.objects.all():
        funcionario, criado = Funcionario.objects.get_or_create(
            usuario=empresa.user,
            empresa=empresa,
            defaults={
                'cargo': 'admin_empresa',
                'pode_baixar_emprestimos': True,
                'pode_regularizar_parcelas': True,
                'pode_configurar_empresa': True,
                'ativo': True
            }
        )
        if criado:
            print(f"✅ Administrador criado para empresa existente: {empresa.nome}")