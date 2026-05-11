# notifications.py do firebase_admin
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification

def enviar_notificacao(usuario_id, titulo, mensagem, url='/'):
    """Envia notificação push para um usuário"""
    devices = FCMDevice.objects.filter(user_id=usuario_id, active=True)
    
    if not devices.exists():
        print(f"Nenhum dispositivo para usuário {usuario_id}")
        return False
    
    message = Message(
        notification=Notification(
            title=titulo,
            body=mensagem
        ),
        data={'url': url}
    )
    
    try:
        devices.send_message(message)
        print(f"✅ Notificação enviada para {usuario_id}")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

# Função de teste
def testar_notificacao(email_usuario):
    """Envia notificação de teste"""
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(email=email_usuario)
        return enviar_notificacao(user.id, "🧪 Teste CODE-MIND", "Notificações funcionando!", "/dashboard/")
    except User.DoesNotExist:
        print(f"Usuário não encontrado: {email_usuario}")
        return False