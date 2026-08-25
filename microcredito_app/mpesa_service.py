
import requests
import json
import uuid
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def formatar_telefone_mz(telefone):
    """Garante que o telefone esta no formato +258XXXXXXXXX"""
    numeros = ''.join(filter(str.isdigit, telefone))
    if numeros.startswith('258'):
        return f'+{numeros}'
    elif len(numeros) == 9:
        return f'+258{numeros}'
    return f'+{numeros}'


class NetShopService:
    """Integracao com a API NetShop (LIVE, sem sandbox)"""

    def __init__(self):
        self.api_key = settings.NETSHOP_API_KEY
        self.wallet_id = settings.NETSHOP_WALLET_ID
        self.base_url = 'https://www.netshop.co.mz/api/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'X-Wallet-ID': self.wallet_id,
            'Content-Type': 'application/json',
        }

    def criar_cobranca(self, telefone, valor, referencia, metodo='emola'):
        """
        Cria uma cobranca (charge). Para carteiras moveis (mpesa/emola/mkesh)
        o telefone (msisdn) e obrigatorio. Para card, nao e necessario.
        """
        payload = {
            'amount': float(valor),
            'currency': 'MZN',
            'method': metodo,  # card | mpesa | emola | mkesh
            'reference': referencia,
        }

        if metodo in ('mpesa', 'emola', 'mkesh'):
            if not telefone:
                return {'error': 'Telefone e obrigatorio para pagamentos via carteira movel.'}
            payload['msisdn'] = formatar_telefone_mz(telefone)

        headers = dict(self.headers)
        headers['Idempotency-Key'] = str(uuid.uuid4())

        print(f"📤 Payload NetShop: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                f"{self.base_url}/charges",
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao chamar NetShop: {e}")
            return {'error': f'Erro de conexao com NetShop: {e}'}

        if response.status_code in (200, 201):
            data = response.json()
            return {
                'sucesso': True,
                'id': data.get('id'),
                'status': data.get('status'),
                'checkout_url': data.get('checkout', {}).get('hosted_url'),
                'raw': data,
            }
        else:
            logger.error(f"NetShop recusou. Status: {response.status_code}, Resposta: {response.text}")
            print(f"❌ NetShop ERROR {response.status_code}: {response.text}")
            return {'error': f'NetShop retornou {response.status_code}: {response.text}'}

    def verificar_status(self, charge_id):
        """Consulta o estado atual de uma cobranca (fonte de verdade)"""
        try:
            response = requests.get(
                f"{self.base_url}/charges/{charge_id}",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return {'status': data.get('status'), 'raw': data}
            elif response.status_code == 404:
                return {'error': 'charge_not_found'}
            return {'error': f'{response.status_code}: {response.text}'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}