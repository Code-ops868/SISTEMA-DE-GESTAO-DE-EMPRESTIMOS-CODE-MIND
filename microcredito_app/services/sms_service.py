import requests
import os
from pathlib import Path

# Lê o arquivo .env manualmente
def ler_env():
    """Lê o arquivo .env e retorna um dicionário com as variáveis"""
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith('#') and '=' in linha:
                    chave, valor = linha.split('=', 1)
                    env_vars[chave.strip()] = valor.strip()
    return env_vars

# Carregar variáveis
ENV_VARS = ler_env()

class ASPSMSService:
    """
    Serviço de SMS usando ASPSMS
    """
    
    def __init__(self):
        # Pega as credenciais do arquivo .env lido manualmente
        self.userkey = ENV_VARS.get('ASPSMS_USERKEY', '')
        self.password = ENV_VARS.get('ASPSMS_PASSWORD', '')
        self.api_url = "https://json.aspsms.com/SendTextSMS"
        
        print(f"📁 .env encontrado: {Path(__file__).resolve().parent.parent.parent / '.env'}")
        print(f"🔑 ASPSMS_USERKEY: {'✅ Configurado' if self.userkey else '❌ NÃO CONFIGURADO'}")
        print(f"🔑 ASPSMS_PASSWORD: {'✅ Configurado' if self.password else '❌ NÃO CONFIGURADO'}")
        
        if not self.userkey or not self.password:
            print("❌ ASPSMS não configurado! Verifique o arquivo .env")
    
    def enviar_sms(self, telefone, mensagem, originator="CODE-MIND"):
        if not self.userkey or not self.password:
            print("❌ Credenciais ASPSMS não configuradas")
            return False
        
        # Limpar telefone
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        if not telefone_limpo.startswith('258'):
            telefone_limpo = f"258{telefone_limpo}"
        
        payload = {
            "Userkey": self.userkey,
            "Password": self.password,
            "Recipients": [telefone_limpo],
            "MessageText": mensagem,
            "Originator": originator
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            resposta = response.json()
            
            if response.status_code == 200 and resposta.get('StatusInfo'):
                print(f"✅ SMS enviado para {telefone}")
                return True
            else:
                print(f"❌ Erro ASPSMS: {resposta}")
                return False
                
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return False