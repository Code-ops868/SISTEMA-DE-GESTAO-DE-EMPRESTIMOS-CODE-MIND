import requests
import json

import uuid
from datetime import datetime
from decouple import config
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class MPESAService:
    """Integração corrigida com a API PaySuite (Sandbox)"""
    
    def __init__(self):
        # Chaves do .env
        self.api_key = config('PAYSUITE_API_KEY')
        self.webhook_secret = config('PAYSUITE_WEBHOOK_SECRET')
        
        # ✅ CORREÇÃO CRÍTICA: Usar a URL exata da sua documentação
        self.base_url = 'https://paysuite.tech/api/v1'
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        logger.info(f"PaySuite Service inicializado. URL: {self.base_url}")

    

    def verificar_status(self, checkout_request_id):
        """Consulta o status do pagamento"""
        try:
            response = requests.get(
                f"{self.base_url}/payments/{checkout_request_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                status = data.get('status') # pending, completed, failed
                
                if status == 'completed':
                    return {'ResultCode': '0', 'ResultDesc': 'Success'}
                elif status == 'failed':
                    return {'ResultCode': '1032', 'ResultDesc': 'Failed'}
                else:
                    return {'ResultCode': '1037', 'ResultDesc': 'Pending'}
            return {'error': 'Consulta falhou'}
        except Exception as e:
            return {'error': str(e)}
    #================================================================================================
    def stk_push(self, telefone, valor, referencia):
            from django.conf import settings
            
            # Payload SEM telefone (cliente insere no checkout)
            payload = {
                'amount': float(valor),
                'method': 'emola',
                'reference': referencia,
                'description': f'Pagamento assinatura - {referencia}',
                'callback_url': settings.PAYSUITE_CALLBACK_URL,
                'return_url': settings.PAYSUITE_RETURN_URL,
            }
            
            # SEM 'beneficiary', SEM 'customer', SEM 'contact', SEM 'phone'
            
            print(f"📤 Payload (sem telefone): {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/payments",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json().get('data', {})
                return {
                    'CheckoutRequestID': data.get('id'),
                    'MerchantRequestID': referencia,
                    'ResponseCode': '0',
                    'ResponseDescription': 'Success',
                    'checkout_url': data.get('checkout_url')  # ← Cliente será redirecionado aqui
                }
            # ... resto do código