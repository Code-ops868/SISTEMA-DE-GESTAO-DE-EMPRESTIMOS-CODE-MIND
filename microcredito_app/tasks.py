from celery import shared_task
from django.core.management import call_command

@shared_task
def enviar_notificacoes_automaticas():
    """
    Tarefa agendada para enviar notificações de atraso e vencimento
    """
    call_command('enviar_notificacoes')
    return "Notificações enviadas com sucesso"