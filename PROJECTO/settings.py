"""
Django settings for PROJECTO project.

Versão revisada: segredos movidos para variáveis de ambiente,
bugs de configuração corrigidos, e hardening de segurança aplicado
(django-axes contra força bruta, honeypot contra bots, headers seguros).
"""

from pathlib import Path
import os
from celery.schedules import crontab
from decouple import config
import firebase_admin
from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# SEGREDOS — TODOS vêm do ambiente (.env local / secrets no Fly.io)
# NUNCA volte a colocar valores reais aqui no código.
# ============================================
#SECRET_KEY = config('SECRET_KEY')  # gere um novo com get_random_secret_key()
SECRET_KEY = config('SECRET_KEY', default='django-insecure-temporary-key')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='projecto.fly.dev,localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://projecto.fly.dev',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# ============================================
# COOKIES / TRANSPORTE SEGURO
# ============================================
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Fly.io fica atrás de um proxy — sem isto, o Django não sabe que a
# conexão original já era HTTPS e pode gerar redirect loops.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG

# HSTS — só ative depois de confirmar que HTTPS está 100% estável
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# ============================================
# APPS
# ============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'crispy_forms',
    'crispy_bootstrap5',
    'microcredito_app.apps.MicrocreditoAppConfig',
    'fcm_django',
    'rest_framework',
    'anymail',

    # --- Segurança ---
    'axes',            # bloqueio por força bruta no login
    'honeypot',
    #'django-honeypot',  # campo-armadilha anti-bot em formulários
]

# nome correto da configuração (o original tinha um typo:
# CRISPY_ALLOWED_TEMPLATE não existe, é CRISPY_ALLOWED_TEMPLATE_PACKS)
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ============================================
# E-MAIL — UMA ÚNICA definição (o original tinha 3, e a última
# sobrescrevia as outras silenciosamente, fazendo os e-mails
# "reais" nunca serem enviados em produção)
# ============================================
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'

ANYMAIL = {
    "BREVO_API_KEY": config('BREVO_API_KEY', default=''),
}
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='CODE-MIND <no-reply@example.com>')

# Fallback SMTP (caso precise trocar de provedor sem mudar código)
EMAIL_HOST = config('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# ============================================
# MIDDLEWARE
# axes.middleware.AxesMiddleware DEVE vir por último
# ============================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'microcredito_app.middleware.PermissaoMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'PROJECTO.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'microcredito_app/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'microcredito_app.context_processors.notificacoes',
            ],
        },
    },
]

WSGI_APPLICATION = 'PROJECTO.wsgi.application'

# ============================================
# BANCO DE DADOS
# ============================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='microcredito_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True





STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')



LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'inicio'

# ============================================
# AUTENTICAÇÃO — AxesBackend PRIMEIRO na lista,
# senão o bloqueio de força bruta não funciona
# ============================================
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ============================================
# DJANGO-AXES — proteção contra força bruta no login
# ============================================
AXES_FAILURE_LIMIT = 5                 # tentativas antes de bloquear
AXES_COOLOFF_TIME = 1                  # horas de bloqueio
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # combina usuário + IP
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ADMIN = True

# ============================================
# FIREBASE — inicialização protegida contra falha
# (antes: um JSON malformado derrubava o projeto inteiro no boot)
# ============================================
FIREBASE_CONFIG = {
    'apiKey': config('FIREBASE_API_KEY', default=''),
    'authDomain': config('FIREBASE_AUTH_DOMAIN', default=''),
    'projectId': config('FIREBASE_PROJECT_ID', default=''),
    'storageBucket': config('FIREBASE_STORAGE_BUCKET', default=''),
    'messagingSenderId': config('FIREBASE_SENDER_ID', default=''),
    'appId': config('FIREBASE_APP_ID', default=''),
    'measurementId': config('FIREBASE_MEASUREMENT_ID', default=''),
}
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'firebase-service-account.json')

if os.path.exists(FIREBASE_CREDENTIALS_PATH):
    try:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        # não deixa um JSON inválido derrubar o deploy inteiro
        import logging
        logging.getLogger('django').error(f"Falha ao iniciar Firebase: {e}")

VAPID_PUBLIC_KEY = config('VAPID_PUBLIC_KEY', default='')
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY', default='')
VAPID_EMAIL = config('VAPID_EMAIL', default='')

# ============================================
# CELERY
# ============================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6380/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6380/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'enviar-notificacoes-a-cada-hora': {
        'task': 'microcredito_app.tasks.enviar_notificacoes_automaticas',
        'schedule': crontab(minute=0, hour='*/1'),
    },
}

FCM_DJANGO_SETTINGS = {
    "ONE_DEVICE_PER_USER": True,
    "DELETE_INACTIVE_DEVICES": True,
}

# ============================================
# PAYSUITE — uma única fonte de verdade (o original tinha
# um dict com placeholders E variáveis de ambiente conflitando)
# ============================================
PAYSUITE_API_KEY = config('PAYSUITE_API_KEY', default='')
PAYSUITE_WEBHOOK_SECRET = config('PAYSUITE_WEBHOOK_SECRET', default='')
PAYSUITE_ACCOUNT_ID = config('PAYSUITE_ACCOUNT_ID', default='')
PAYSUITE_ENVIRONMENT = config('PAYSUITE_ENVIRONMENT', default='sandbox')
PAYSUITE_CALLBACK_URL = config('PAYSUITE_CALLBACK_URL', default='')
PAYSUITE_RETURN_URL = config('PAYSUITE_RETURN_URL', default='')
PAYSUITE_TIMEOUT = config('PAYSUITE_TIMEOUT', default=30, cast=int)
PAYSUITE_MAX_RETRIES = config('PAYSUITE_MAX_RETRIES', default=3, cast=int)

# ============================================
# NETSHOP — gateway de pagamentos (substitui PaySuite)
# ============================================
NETSHOP_API_KEY = config('NETSHOP_API_KEY', default='')
NETSHOP_WALLET_ID = config('NETSHOP_WALLET_ID', default='')
NETSHOP_WEBHOOK_SECRET = config('NETSHOP_WEBHOOK_SECRET', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'