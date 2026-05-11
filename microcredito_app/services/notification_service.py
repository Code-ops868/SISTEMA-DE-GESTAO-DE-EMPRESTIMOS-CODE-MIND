import requests
import json
from datetime import date, timedelta
from django.utils import timezone
from decouple import config

class NotificationService:
    """Serviço de envio de notificações via WhatsApp e SMS"""
    
    # ============================================
    # CONFIGURAÇÕES (usar credenciais reais depois)
    # ============================================
    WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/{phone_id}/messages"
    SMS_API_URL = "https://api.smsprovider.com/send"
    
    @staticmethod
    def enviar_whatsapp(telefone, mensagem, token, phone_id):
        """Enviar mensagem via WhatsApp Business API"""
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        if not telefone_limpo.startswith('258'):
            telefone_limpo = f"258{telefone_limpo}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': telefone_limpo,
            'type': 'text',
            'text': {'body': mensagem}
        }
        
        try:
            url = NotificationService.WHATSAPP_API_URL.format(phone_id=phone_id)
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Erro WhatsApp: {e}")
            return False
    
    @staticmethod
    def enviar_sms(telefone, mensagem, api_key):
        """Enviar mensagem via SMS"""
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        if not telefone_limpo.startswith('258'):
            telefone_limpo = f"258{telefone_limpo}"
        
        try:
            # Exemplo com provedor SMS (ajustar conforme provedor)
            response = requests.post(
                NotificationService.SMS_API_URL,
                json={'to': telefone_limpo, 'message': mensagem, 'api_key': api_key},
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Erro SMS: {e}")
            return False
    
    @staticmethod
    def formatar_moeda(valor):
        return f"MT {valor:,.2f}".replace(',', '.')
    
    @staticmethod
    def mensagem_vencimento(cliente, parcela, dias_restantes):
        """Mensagem para vencimento próximo"""
        return f"""🔔 Lembrete de Pagamento - {cliente.empresa.nome}

Olá {cliente.nome}!

⚠️ Faltam {dias_restantes} dias para o vencimento da sua parcela.

📅 Parcela: {parcela.numero}
💰 Valor: {NotificationService.formatar_moeda(parcela.valor)}
📆 Vencimento: {parcela.data_vencimento.strftime('%d/%m/%Y')}

Pague antes do vencimento para evitar multas e juros!

Dúvidas? Fale conosco: {cliente.empresa.telefone}"""
    
    @staticmethod
    def mensagem_atraso(cliente, parcela, dias_atraso, multa, juros, valor_total):
        """Mensagem para atraso"""
        return f"""⚠️ ALERTA DE ATRASO - {cliente.empresa.nome}

Olá {cliente.nome}!

Sua parcela está em atraso!

📅 Parcela: {parcela.numero}
💰 Valor Original: {NotificationService.formatar_moeda(parcela.valor)}
⚠️ Multa (2%): +{NotificationService.formatar_moeda(multa)}
📈 Juros: +{NotificationService.formatar_moeda(juros)}
━━━━━━━━━━━━━━━━━━━━
💸 Total a Pagar: {NotificationService.formatar_moeda(valor_total)}
⏰ Dias em atraso: {dias_atraso}

Regularize já para evitar mais juros!

Dúvidas? Fale conosco: {cliente.empresa.telefone}"""
    
    @staticmethod
    def mensagem_cobranca_credor(empresa, parcelas_vencendo, parcelas_atrasadas):
        """Mensagem para o credor (empresa)"""
        msg = f"""📊 RELATÓRIO DE COBRANÇA - {empresa.nome}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 PRÓXIMOS VENCIMENTOS ({len(parcelas_vencendo)} parcelas)
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for p in parcelas_vencendo[:5]:
            msg += f"\n• {p.emprestimo.cliente.nome}: {NotificationService.formatar_moeda(p.valor)} - Vence em {p.data_vencimento.strftime('%d/%m')}"
        
        msg += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ PARCELAS EM ATRASO ({len(parcelas_atrasadas)} parcelas)\n━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        for p in parcelas_atrasadas[:5]:
            msg += f"\n• {p.emprestimo.cliente.nome}: {NotificationService.formatar_moeda(p.valor)} - Atraso {p.dias_atraso} dias"
        
        msg += f"\n\n📞 Entre em contato com os clientes para regularização.\nCODE-MIND - Gestão de Empréstimos"
        
        return msg
#--------------------------sms service-------------------------------
# microcredito_app/services/notification_service.py
from .sms_service import ASPSMSService

class NotificationService:
    
    def __init__(self):
        self.sms = ASPSMSService()
    
    def enviar_sms_notificacao(self, telefone, mensagem):
        """Envia SMS usando o serviço ASPSMS"""
        return self.sms.enviar_sms(telefone, mensagem)
    
    def enviar_notificacao_vencimento(self, cliente, parcela, dias_restantes):
        """Envia SMS de vencimento para o cliente"""
        mensagem = self.mensagem_vencimento(cliente, parcela, dias_restantes)
        return self.enviar_sms_notificacao(cliente.telefone, mensagem)