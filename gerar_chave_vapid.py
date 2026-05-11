# gerar_chaves_vapid.py
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Gerar par de chaves
private_key = ec.generate_private_key(ec.SECP256r1())
public_key = private_key.public_key()

# Converter para formato PKCS8
vapid_private_key = base64.urlsafe_b64encode(
    private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
).decode('utf-8').rstrip('=')

vapid_public_key = base64.urlsafe_b64encode(
    public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
).decode('utf-8').rstrip('=')

print("\n" + "="*60)
print("✅ CHAVES VAPID GERADAS COM SUCESSO!")
print("="*60)
print("\n🔑 COPIE PARA O settings.py:\n")
print(f"VAPID_PUBLIC_KEY = '{vapid_public_key}'")
print(f"VAPID_PRIVATE_KEY = '{vapid_private_key}'")
print(f"VAPID_EMAIL = 'contato@codemind.com'\n")
print("="*60)