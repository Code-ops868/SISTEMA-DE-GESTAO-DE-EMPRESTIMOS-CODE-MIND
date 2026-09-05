import logging
import hmac
import hashlib
import json
import re
import uuid
import secrets
from io import BytesIO
from datetime import date, datetime, timedelta
from decimal import Decimal

import dns.resolver
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from fcm_django.models import FCMDevice

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import (
    Parcela, Pagamento, Emprestimo, Cliente,
    Assinatura, Plano, PagamentoAssinatura, TransacaoMPESA,
    Empresa, PushSubscription, EmailVerificacao,
    ConfiguracaoNotificacao, Funcionario,
)
from .mpesa_service import NetShopService
from .forms import CadastroForm, LoginForm, ClienteForm

logger = logging.getLogger('django')

# Domínios de e-mail temporário/descartável bloqueados no cadastro
DOMINIOS_EMAIL_BLOQUEADOS = [
    'temp-mail.com', 'mailinator.com', 'guerrillamail.com',
    '10minutemail.com', 'throwawaymail.com', 'yopmail.com',
    'fakeinbox.com', 'mailnator.com', 'getairmail.com',
    'sharklasers.com', 'guerrillamail.net', 'guerrillamail.org',
    'mailmetrash.com', 'trashmail.com', 'tempemail.net',
    'tempmail.com', 'mohmal.com', 'dispostable.com',
]


# ============================================
# FUNÇÕES DE VALIDAÇÃO DE DOCUMENTOS MOÇAMBICANOS
# ============================================

def validar_nuit(nuit):
    """
    Valida NUIT (Número Único de Identificação Tributária)
    - Deve ter 9 dígitos numéricos
    """
    if not nuit:
        return True, None
    
    nuit = str(nuit).strip()
    if not re.match(r'^[0-9]{9}$', nuit):
        return False, 'NUIT deve ter exatamente 9 dígitos numéricos.'
    
    return True, None


def validar_nuib(nuib):
    """
    Valida NUIB (Número Único de Identificação do Bilhete)
    - Deve ter 9 dígitos numéricos
    """
    if not nuib:
        return True, None
    
    nuib = str(nuib).strip()
    if not re.match(r'^[0-9]{9}$', nuib):
        return False, 'NUIB deve ter exatamente 9 dígitos numéricos.'
    
    return True, None
#=================NOVA FUNCAO==============================
def validar_dire(dire):
    """
    Valida DIRE (Documento de Identificação de Residentes Estrangeiros)
    Formato: 13 dígitos + 1 letra (Módulo 23)
    """
    if not dire:
        return True, None
    
    dire = str(dire).strip().upper()
    
    # DIRE: 13 dígitos + 1 letra
    match = re.match(r'^([0-9]{13})([A-Z])$', dire)
    if not match:
        return False, 'Formato: 13 dígitos + letra (ex: 1234567890123X)'
    
    numeros = match.group(1)
    letra_informada = match.group(2)
    
    # Módulo 23
    letras = 'ABCDEFGHJKLMNPQRSTVWXYZ'
    peso = 0
    for i, digito in enumerate(numeros):
        peso += int(digito) * (i + 1)
    
    resto = peso % 23
    letra_calculada = letras[resto - 1] if resto > 0 else 'Z'
    
    if letra_informada == letra_calculada:
        return True, None
    
    return False, f'Letra inválida. Correta: {letra_calculada}'
#==============================================================================================
def validar_bi_passaporte(bi_passaporte):
    """
    Valida BI Moçambicano: 13 dígitos + letra (Módulo 23)
    """
    if not bi_passaporte:
        return True, None, None
    
    bi = str(bi_passaporte).strip().upper()
    
    # BI: 13 dígitos + 1 letra
    match = re.match(r'^([0-9]{13})([A-Z])$', bi)
    if not match:
        return False, 'Formato: 13 dígitos + letra (ex: 031123456789B)', None
    
    numeros = match.group(1)
    letra_informada = match.group(2)
    
    # Módulo 23
    letras = 'ABCDEFGHJKLMNPQRSTVWXYZ'
    peso = 0
    for i, digito in enumerate(numeros):
        peso += int(digito) * (i + 1)
    
    resto = peso % 23
    letra_calculada = letras[resto - 1] if resto > 0 else 'Z'
    
    if letra_informada == letra_calculada:
        return True, None, 'BI'
    
    return False, f'Letra inválida. Correta: {letra_calculada}', None
#=============================================================================================
def validar_documentos_cliente(data):
    errors = {}
    is_valid = True
    
    # NUIT
    nuit_valid, nuit_error = validar_nuit(data.get('nuit'))
    if not nuit_valid:
        errors['nuit'] = nuit_error
        is_valid = False
    
    # NUIB
    nuib_valid, nuib_error = validar_nuib(data.get('nuib'))
    if not nuib_valid:
        errors['nuib'] = nuib_error
        is_valid = False
    
    # BI/Passaporte
    bi = data.get('bi_passaporte')
    if bi:
        # Verificar se é DIRE
        dire_valid, dire_error = validar_dire(bi)
        if dire_valid:
            # É um DIRE válido
            pass
        else:
            # Tentar validar como BI
            bi_valid, bi_error, bi_tipo = validar_bi_passaporte(bi)
            if not bi_valid:
                errors['bi_passaporte'] = bi_error
                is_valid = False
    
    # Validar datas
    data_emissao = data.get('data_emissao_documento')
    data_validade = data.get('data_validade_documento')
    
    if data_emissao and data_validade:
        try:
            if isinstance(data_emissao, str):
                emissao = datetime.strptime(data_emissao, '%Y-%m-%d').date()
            else:
                emissao = data_emissao
                
            if isinstance(data_validade, str):
                validade = datetime.strptime(data_validade, '%Y-%m-%d').date()
            else:
                validade = data_validade
            
            if emissao > validade:
                errors['data_validade_documento'] = 'A data de validade deve ser posterior à data de emissão.'
                is_valid = False
            
            if validade < date.today():
                errors['data_validade_documento'] = 'O documento está vencido.'
                is_valid = False
                
        except (ValueError, TypeError):
            errors['data_emissao_documento'] = 'Data inválida.'
            is_valid = False
    
    return is_valid, errors

#==============================================================================================
def verificar_documento_unico(model, campo, valor, usuario, excluir_id=None):
    """
    Verifica se um documento já está cadastrado para outro cliente
    Retorna (is_unique, error_message)
    """
    if not valor:
        return True, None
    
    queryset = model.objects.filter(**{campo: valor}, usuario=usuario)
    if excluir_id:
        queryset = queryset.exclude(id=excluir_id)
    
    if queryset.exists():
        nome_campo = dict(model._meta.fields)[campo].verbose_name
        return False, f'{nome_campo} "{valor}" já está cadastrado para outro cliente.'
    
    return True, None


# ============================================
# PÁGINAS PÚBLICAS
# ============================================

def inicio(request):
    return render(request, 'inicio.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            senha = form.cleaned_data['senha']
            lembrar = form.cleaned_data['lembrar']

            erro_generico = 'E-mail ou senha incorretos.'

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, erro_generico)
                return render(request, 'auth/login.html', {'form': form})

            user_authenticated = authenticate(request, username=user.username, password=senha)

            if not user_authenticated:
                messages.error(request, erro_generico)
                return render(request, 'auth/login.html', {'form': form})

            login(request, user_authenticated)
            if not lembrar:
                request.session.set_expiry(0)

            try:
                assinatura = Assinatura.objects.get(usuario=user_authenticated)
                if assinatura.status != 'ativa':
                    messages.info(request, 'Escolha um plano para acessar o sistema.')
                    return redirect('planos')
            except Assinatura.DoesNotExist:
                messages.info(request, 'Escolha um plano para acessar o sistema.')
                return redirect('planos')

            messages.success(request, f'Bem-vindo de volta, {user.first_name or user.username}!')
            return redirect('dashboard')

        for error in form.errors.values():
            messages.error(request, error)
        return render(request, 'auth/login.html', {'form': form})

    form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        telefone = request.POST.get('telefone', '').strip()
        senha1 = request.POST.get('senha1', '')
        senha2 = request.POST.get('senha2', '')
        termos = request.POST.get('termos')

        if not email:
            messages.error(request, 'E-mail é obrigatório.')
            return render(request, 'auth/cadastro.html')

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            messages.error(request, 'Digite um e-mail válido (exemplo: nome@dominio.com)')
            return render(request, 'auth/cadastro.html')

        dominio = email.split('@')[1].lower()
        if dominio in DOMINIOS_EMAIL_BLOQUEADOS:
            messages.error(request, 'Não é permitido usar e-mails temporários ou descartáveis.')
            return render(request, 'auth/cadastro.html')

        try:
            dns.resolver.resolve(dominio, 'MX')
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers) as e:
            logger.warning("Domínio de e-mail sem MX válido no cadastro: %s (%s)", dominio, e)
        except dns.exception.Timeout:
            logger.warning("Timeout ao validar MX do domínio: %s", dominio)

        if not termos:
            messages.error(request, 'Você deve aceitar os termos de uso.')
            return render(request, 'auth/cadastro.html')

        if not first_name or not last_name:
            messages.error(request, 'Nome e sobrenome são obrigatórios.')
            return render(request, 'auth/cadastro.html')

        if not telefone:
            messages.error(request, 'Telefone é obrigatório.')
            return render(request, 'auth/cadastro.html')

        if senha1 != senha2:
            messages.error(request, 'As senhas não conferem.')
            return render(request, 'auth/cadastro.html')

        try:
            validate_password(senha1)
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return render(request, 'auth/cadastro.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail já está cadastrado.')
            return render(request, 'auth/cadastro.html')

        username_base = email.split('@')[0]
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=senha1,
                first_name=first_name,
                last_name=last_name,
            )

            user.is_active = False
            user.save()

            codigo = secrets.token_urlsafe(32)
            expiracao = timezone.now() + timedelta(hours=24)

            EmailVerificacao.objects.create(
                usuario=user,
                codigo=codigo,
                expira_em=expiracao,
            )

            link = request.build_absolute_uri(f'/confirmar-email/{codigo}/')

            try:
                from django.core.mail import send_mail
                send_mail(
                    subject='Confirme seu cadastro - CODE-MIND',
                    message=(
                        f'Olá {first_name}!\n\n'
                        f'Obrigado por se cadastrar na CODE-MIND.\n\n'
                        f'Para ativar sua conta e começar a usar o sistema, clique no link abaixo:\n\n'
                        f'{link}\n\n'
                        f'Este link é válido por 24 horas.\n\n'
                        f'Se você não solicitou este cadastro, ignore este email.\n\n'
                        f'Atenciosamente,\nEquipe CODE-MIND'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f'Cadastro realizado, {first_name}! Enviamos um link de confirmação '
                    f'para seu email. Verifique sua caixa de entrada.'
                )
            except Exception as e:
                logger.error("Erro ao enviar email de confirmação para %s: %s", email, e)
                messages.warning(
                    request,
                    'Cadastro realizado, mas houve erro ao enviar email de confirmação. '
                    'Entre em contato com o suporte.'
                )

            return redirect('login')

        except Exception as e:
            logger.error("Erro ao criar conta para %s: %s", email, e)
            messages.error(request, 'Erro ao criar conta. Tente novamente.')
            return render(request, 'auth/cadastro.html')

    return render(request, 'auth/cadastro.html')


def confirmar_email_view(request, codigo):
    """Confirma o email do usuário e ativa a conta"""
    try:
        verificacao = EmailVerificacao.objects.get(codigo=codigo)

        if verificacao.verificado_em:
            messages.warning(request, 'Este email já foi verificado. Faça login.')
            return redirect('login')

        if timezone.now() > verificacao.expira_em:
            messages.error(request, 'Este link de confirmação expirou. Solicite um novo.')
            return redirect('login')

        user = verificacao.usuario
        user.is_active = True
        user.save()

        verificacao.verificado_em = timezone.now()
        verificacao.save()

        messages.success(request, 'Email confirmado! Agora você pode fazer login.')
        return redirect('login')

    except EmailVerificacao.DoesNotExist:
        messages.error(request, 'Link de confirmação inválido.')
        return redirect('login')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('inicio')


# ============================================
# DECORATOR PARA VERIFICAR ASSINATURA
# ============================================

def verificar_assinatura(view_func):
    """Decorator para verificar se o usuário tem assinatura ativa"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff:
            return view_func(request, *args, **kwargs)

        try:
            assinatura = Assinatura.objects.get(usuario=request.user)
            if assinatura.status != 'ativa':
                messages.warning(request, 'Escolha um plano para acessar o sistema.')
                return redirect('planos')
        except Assinatura.DoesNotExist:
            messages.warning(request, 'Escolha um plano para acessar o sistema.')
            return redirect('planos')

        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# DASHBOARD
# ============================================

@login_required
@verificar_assinatura
def dashboard(request):
    if not request.user.is_staff:
        try:
            assinatura = Assinatura.objects.get(usuario=request.user)
            if assinatura.status in ['teste', 'expirada']:
                messages.warning(request, 'Sua assinatura expirou. Escolha um plano para continuar.')
                return redirect('planos')
        except Assinatura.DoesNotExist:
            return redirect('planos')

    usuario = request.user
    hoje = date.today()

    total_clientes = Cliente.objects.filter(usuario=usuario).count()
    emprestimos_ativos = Emprestimo.objects.filter(usuario=usuario, status='ativo').count()
    total_emprestado = Emprestimo.objects.filter(usuario=usuario).aggregate(Sum('valor'))['valor__sum'] or 0

    inicio_mes = datetime(hoje.year, hoje.month, 1).date()
    recebido_mes = Pagamento.objects.filter(
        parcela__emprestimo__usuario=usuario,
        data_pagamento__date__gte=inicio_mes
    ).aggregate(Sum('valor'))['valor__sum'] or 0

    ultimos_emprestimos = Emprestimo.objects.filter(usuario=usuario).select_related('cliente').order_by('-criado_em')[:5]
    proximas_parcelas = Parcela.objects.filter(
        emprestimo__usuario=usuario,
        status='pendente',
        data_vencimento__gte=hoje
    ).select_related('emprestimo__cliente').order_by('data_vencimento')[:5]

    status_data = Emprestimo.objects.filter(usuario=usuario).values('status').annotate(total=Count('id'))
    monthly_labels = []
    monthly_data = []
    for i in range(5, -1, -1):
        data = hoje - timedelta(days=30 * i)
        monthly_labels.append(data.strftime('%b/%Y'))
        total = Emprestimo.objects.filter(
            usuario=usuario,
            data_contrato__year=data.year,
            data_contrato__month=data.month
        ).aggregate(Sum('valor'))['valor__sum'] or 0
        monthly_data.append(float(total))

    context = {
        'total_clientes': total_clientes,
        'emprestimos_ativos': emprestimos_ativos,
        'total_emprestado': total_emprestado,
        'recebido_mes': recebido_mes,
        'ultimos_emprestimos': ultimos_emprestimos,
        'proximas_parcelas': proximas_parcelas,
        'status_labels': [dict(Emprestimo.STATUS_CHOICES).get(s['status'], s['status']) for s in status_data],
        'status_data': [s['total'] for s in status_data],
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
    }
    return render(request, 'core/dashboard.html', context)


# ============================================
# PLANOS E ASSINATURAS
# ============================================

def planos(request):
    planos_lista = Plano.objects.all()
    assinatura = None
    dias_restantes = 0

    if request.user.is_authenticated:
        try:
            assinatura = Assinatura.objects.get(usuario=request.user)
            dias_restantes = max(0, (assinatura.data_expiracao - timezone.now()).days)
        except Assinatura.DoesNotExist:
            pass

    context = {
        'assinatura': assinatura,
        'dias_restantes': dias_restantes,
        'planos': planos_lista,
    }
    return render(request, 'planos/lista.html', context)


@login_required
def pagamento_plano(request, plano_nome):
    try:
        Plano.objects.get(nome=plano_nome)
    except Plano.DoesNotExist:
        messages.error(request, 'Plano não encontrado.')
        return redirect('planos')

    return redirect('pagamento_mpesa', plano_nome=plano_nome)


@login_required
def pagamento_mpesa(request, plano_nome):
    try:
        plano = Plano.objects.get(nome=plano_nome)
    except Plano.DoesNotExist:
        messages.error(request, 'Plano não encontrado.')
        return redirect('planos')

    if request.method == 'GET':
        return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})

    if request.method == 'POST':
        metodo = request.POST.get('metodo_pagamento', 'emola')
        telefone = request.POST.get('telefone', '').strip()

        if metodo in ('mpesa', 'emola', 'mkesh') and not telefone:
            messages.error(request, 'Informe o número de telefone para pagamentos via M-Pesa/e-Mola.')
            return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})

        nome_limpo = re.sub(r'[^A-Za-z]', '', plano.nome.upper())
        referencia = f"PLANO{nome_limpo}{uuid.uuid4().hex[:12].upper()}"

        transacao = TransacaoMPESA.objects.create(
            usuario=request.user,
            plano=plano,
            valor=plano.valor,
            telefone=telefone,
            referencia=referencia,
            status='pendente',
            checkout_request_id=None,
            merchant_request_id=None,
        )

        netshop = NetShopService()
        response = netshop.criar_cobranca(telefone, float(plano.valor), referencia, metodo=metodo)

        if response.get('error'):
            transacao.status = 'falhou'
            transacao.resultado = str(response)
            transacao.save()
            messages.error(request, f'Erro ao iniciar pagamento: {response.get("error")}')
            return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})

        transacao.checkout_request_id = response.get('id')
        transacao.merchant_request_id = referencia
        transacao.status = 'processando'
        transacao.save()

        checkout_url = response.get('checkout_url')
        if checkout_url:
            return redirect(checkout_url)
        else:
            messages.info(request, 'Pagamento iniciado. Confirme no seu telemóvel.')
            return redirect('pagamento_mpesa_status', transacao_id=transacao.id)

    return JsonResponse({'error': 'Método não permitido'}, status=405)


@login_required
def pagamento_mpesa_status(request, transacao_id):
    transacao = get_object_or_404(TransacaoMPESA, id=transacao_id, usuario=request.user)

    if transacao.status == 'sucesso':
        messages.success(request, 'Pagamento confirmado! Sua assinatura foi ativada.')
        return redirect('dashboard')

    if transacao.status == 'falhou':
        messages.error(request, 'Pagamento falhou. Tente novamente.')
        return redirect('planos')

    if transacao.checkout_request_id:
        netshop = NetShopService()
        status_response = netshop.verificar_status(transacao.checkout_request_id)

        status_atual = status_response.get('status')

        if status_atual == 'paid':
            transacao.status = 'sucesso'
            transacao.resultado = json.dumps(status_response.get('raw', {}))
            transacao.save()
            ativar_assinatura(request.user, transacao.plano)
            messages.success(request, 'Pagamento confirmado! Sua assinatura foi ativada.')
            return redirect('dashboard')
        elif status_atual == 'failed':
            transacao.status = 'falhou'
            transacao.resultado = json.dumps(status_response.get('raw', {}))
            transacao.save()
            messages.error(request, 'Pagamento falhou. Tente novamente.')
            return redirect('planos')
        elif status_atual == 'pending':
            messages.info(request, 'Pagamento ainda em processamento. Aguarde a confirmação.')

    return render(request, 'planos/status_mpesa.html', {'transacao': transacao})


@csrf_exempt
def mpesa_callback(request):
    if request.method != 'POST':
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Method not allowed'})

    assinatura_recebida = request.headers.get('X-PaySuite-Signature', '')
    webhook_secret = getattr(settings, 'PAYSUITE_WEBHOOK_SECRET', '')

    if not webhook_secret:
        logger.error("PAYSUITE_WEBHOOK_SECRET não configurado -- recusando webhook.")
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Server misconfigured'}, status=500)

    assinatura_esperada = hmac.new(
        webhook_secret.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(assinatura_recebida, assinatura_esperada):
        logger.warning("Webhook PaySuite recebido com assinatura inválida ou ausente.")
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid signature'}, status=403)

    try:
        data = json.loads(request.body)

        checkout_request_id = None
        result_code = None

        if 'Body' in data:
            callback_data = data.get('Body', {}).get('stkCallback', {})
            result_code = callback_data.get('ResultCode')
            checkout_request_id = callback_data.get('CheckoutRequestID')
        else:
            event = data.get('event')
            event_data = data.get('data', {})

            if event == 'payment.success':
                result_code = '0'
                checkout_request_id = event_data.get('id')
            elif event == 'payment.failed':
                result_code = '1032'
                checkout_request_id = event_data.get('id')

        if result_code == '0':
            transacao = TransacaoMPESA.objects.filter(
                checkout_request_id=checkout_request_id
            ).first()

            if transacao and transacao.status != 'sucesso':
                transacao.status = 'sucesso'
                transacao.resultado = json.dumps(data)
                transacao.save()
                ativar_assinatura(transacao.usuario, transacao.plano)

        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

    except Exception as e:
        logger.error("Erro no webhook PaySuite: %s", e)
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Internal error'})


def ativar_assinatura(usuario, plano):
    assinatura, created = Assinatura.objects.update_or_create(
        usuario=usuario,
        defaults={
            'status': 'ativa',
            'plano': plano,
            'data_inicio': timezone.now(),
            'data_expiracao': timezone.now() + timedelta(days=plano.duracao_dias),
            'data_pagamento': timezone.now(),
        }
    )
    return assinatura


@login_required
def confirmar_pagamento(request, pagamento_id):
    pagamento = get_object_or_404(PagamentoAssinatura, id=pagamento_id)

    if request.user.is_staff:
        pagamento.status = 'pago'
        pagamento.save()

        assinatura, created = Assinatura.objects.get_or_create(usuario=pagamento.usuario)
        assinatura.plano = pagamento.plano
        assinatura.status = 'ativa'
        assinatura.data_inicio = timezone.now()
        assinatura.data_expiracao = timezone.now() + timedelta(days=pagamento.plano.duracao_dias)
        assinatura.data_pagamento = timezone.now()
        assinatura.save()

        messages.success(request, 'Pagamento confirmado! Assinatura ativada.')

    return redirect('admin:index')


@login_required
def simular_callback(request, transacao_id):
    if not (request.user.is_staff and settings.DEBUG):
        return JsonResponse({'error': 'Não disponível.'}, status=404)

    transacao = get_object_or_404(TransacaoMPESA, id=transacao_id, usuario=request.user)

    transacao.status = 'sucesso'
    transacao.save()

    ativar_assinatura(transacao.usuario, transacao.plano)

    return JsonResponse({'status': 'sucesso', 'mensagem': 'Pagamento simulado com sucesso'})


# ============================================
# CLIENTES - ATUALIZADO COM DOCUMENTOS
# ============================================

@login_required
@verificar_assinatura
def lista_clientes(request):
    """Lista de clientes com filtros por documentos"""
    clientes = Cliente.objects.filter(usuario=request.user)
    
    # Filtro de busca geral
    search = request.GET.get('search')
    if search:
        clientes = clientes.filter(
            Q(nome__icontains=search) |
            Q(telefone__icontains=search) |
            Q(email__icontains=search) |
            Q(nuit__icontains=search) |
            Q(nuib__icontains=search) |
            Q(bi_passaporte__icontains=search)
        )
    
    # Filtro por tipo (empresa/pessoa física)
    tipo = request.GET.get('tipo')
    if tipo == 'empresa':
        clientes = clientes.filter(nuit__isnull=False)
    elif tipo == 'pessoa_fisica':
        clientes = clientes.filter(nuit__isnull=True)
    
    return render(request, 'clientes/lista.html', {
        'clientes': clientes,
        'today': date.today(),
    })


@login_required
@verificar_assinatura
def cliente_cadastrar(request):
    """Cadastrar novo cliente com validação de documentos moçambicanos"""
    if request.method == 'POST':
        # Capturar dados do formulário
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        
        # Documentos
        nuit = request.POST.get('nuit', '').strip() or None
        nuib = request.POST.get('nuib', '').strip() or None
        bi_passaporte = request.POST.get('bi_passaporte', '').strip() or None
        data_emissao_documento = request.POST.get('data_emissao_documento', '') or None
        data_validade_documento = request.POST.get('data_validade_documento', '') or None
        
        renda_mensal_raw = request.POST.get('renda_mensal', '').replace('.', '').replace(',', '.')
        data_nascimento = request.POST.get('data_nascimento', '') or None
        endereco = request.POST.get('endereco', '').strip() or None
        observacoes = request.POST.get('observacoes', '').strip() or None

        # Validar campos obrigatórios
        if not nome:
            messages.error(request, 'Nome completo é obrigatório.')
            return render(request, 'clientes/formulario.html', {
                'nome': nome, 'email': email, 'telefone': telefone,
                'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
            })

        if not telefone:
            messages.error(request, 'Telefone é obrigatório.')
            return render(request, 'clientes/formulario.html', {
                'nome': nome, 'email': email, 'telefone': telefone,
                'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
            })

        # Validar documentos
        dados_documentos = {
            'nuit': nuit,
            'nuib': nuib,
            'bi_passaporte': bi_passaporte,
            'data_emissao_documento': data_emissao_documento,
            'data_validade_documento': data_validade_documento,
        }
        
        is_valid, doc_errors = validar_documentos_cliente(dados_documentos)
        
        if not is_valid:
            for campo, erro in doc_errors.items():
                messages.error(request, erro)
            return render(request, 'clientes/formulario.html', {
                'nome': nome, 'email': email, 'telefone': telefone,
                'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
                'data_emissao_documento': data_emissao_documento,
                'data_validade_documento': data_validade_documento,
            })

        # Verificar duplicidade de documentos
        if nuit:
            is_unique, error = verificar_documento_unico(Cliente, 'nuit', nuit, request.user)
            if not is_unique:
                messages.error(request, error)
                return render(request, 'clientes/formulario.html', {
                    'nome': nome, 'email': email, 'telefone': telefone,
                    'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
                })
        
        if nuib:
            is_unique, error = verificar_documento_unico(Cliente, 'nuib', nuib, request.user)
            if not is_unique:
                messages.error(request, error)
                return render(request, 'clientes/formulario.html', {
                    'nome': nome, 'email': email, 'telefone': telefone,
                    'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
                })
        
        if bi_passaporte:
            is_unique, error = verificar_documento_unico(Cliente, 'bi_passaporte', bi_passaporte, request.user)
            if not is_unique:
                messages.error(request, error)
                return render(request, 'clientes/formulario.html', {
                    'nome': nome, 'email': email, 'telefone': telefone,
                    'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
                })

        # Processar renda mensal
        try:
            renda_mensal = float(renda_mensal_raw) if renda_mensal_raw else None
        except ValueError:
            messages.error(request, 'Renda mensal inválida.')
            return render(request, 'clientes/formulario.html', {
                'nome': nome, 'email': email, 'telefone': telefone,
                'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
            })

        # Criar cliente
        try:
            cliente = Cliente.objects.create(
                usuario=request.user,
                nome=nome,
                email=email if email else None,
                telefone=telefone,
                nuit=nuit,
                nuib=nuib,
                bi_passaporte=bi_passaporte,
                data_emissao_documento=data_emissao_documento if data_emissao_documento else None,
                data_validade_documento=data_validade_documento if data_validade_documento else None,
                renda_mensal=renda_mensal,
                data_nascimento=data_nascimento if data_nascimento else None,
                endereco=endereco if endereco else None,
                observacoes=observacoes if observacoes else None,
            )
            
            messages.success(request, f'Cliente "{nome}" cadastrado com sucesso!')
            logger.info(f"Cliente criado: {cliente.id} - {cliente.nome} - Documentos: {cliente.get_documentos_info()}")
            return redirect('clientes')
            
        except Exception as e:
            logger.error(f"Erro ao criar cliente: {e}")
            messages.error(request, 'Erro ao cadastrar cliente. Tente novamente.')
            return render(request, 'clientes/formulario.html', {
                'nome': nome, 'email': email, 'telefone': telefone,
                'nuit': nuit, 'nuib': nuib, 'bi_passaporte': bi_passaporte,
            })

    return render(request, 'clientes/formulario.html')


@login_required
@verificar_assinatura
def cliente_editar(request, id):
    """Editar cliente com validação de documentos moçambicanos"""
    cliente = get_object_or_404(Cliente, id=id, usuario=request.user)

    if request.method == 'POST':
        # Capturar dados
        cliente.nome = request.POST.get('nome', '').strip()
        cliente.email = request.POST.get('email', '').strip() or None
        cliente.telefone = request.POST.get('telefone', '').strip()
        
        # Documentos
        cliente.nuit = request.POST.get('nuit', '').strip() or None
        cliente.nuib = request.POST.get('nuib', '').strip() or None
        cliente.bi_passaporte = request.POST.get('bi_passaporte', '').strip() or None
        cliente.data_emissao_documento = request.POST.get('data_emissao_documento', '') or None
        cliente.data_validade_documento = request.POST.get('data_validade_documento', '') or None
        
        renda_raw = request.POST.get('renda_mensal', '').replace('.', '').replace(',', '.')
        cliente.data_nascimento = request.POST.get('data_nascimento', '') or None
        cliente.endereco = request.POST.get('endereco', '').strip() or None
        cliente.observacoes = request.POST.get('observacoes', '').strip() or None

        # Validar campos obrigatórios
        if not cliente.nome:
            messages.error(request, 'Nome completo é obrigatório.')
            return render(request, 'clientes/formulario.html', {'cliente': cliente})

        if not cliente.telefone:
            messages.error(request, 'Telefone é obrigatório.')
            return render(request, 'clientes/formulario.html', {'cliente': cliente})

        # Validar documentos
        dados_documentos = {
            'nuit': cliente.nuit,
            'nuib': cliente.nuib,
            'bi_passaporte': cliente.bi_passaporte,
            'data_emissao_documento': str(cliente.data_emissao_documento) if cliente.data_emissao_documento else None,
            'data_validade_documento': str(cliente.data_validade_documento) if cliente.data_validade_documento else None,
        }
        
        is_valid, doc_errors = validar_documentos_cliente(dados_documentos)
        
        if not is_valid:
            for campo, erro in doc_errors.items():
                messages.error(request, erro)
            return render(request, 'clientes/formulario.html', {'cliente': cliente})

        # Verificar duplicidade de documentos
        if cliente.nuit:
            is_unique, error = verificar_documento_unico(Cliente, 'nuit', cliente.nuit, request.user, cliente.id)
            if not is_unique:
                messages.error(request, error)
                return render(request, 'clientes/formulario.html', {'cliente': cliente})
        
        if cliente.nuib:
            is_unique, error = verificar_documento_unico(Cliente, 'nuib', cliente.nuib, request.user, cliente.id)
            if not is_unique:
                messages.error(request, error)
                return render(request, 'clientes/formulario.html', {'cliente': cliente})
        
        if cliente.bi_passaporte:
            is_unique, error = verificar_documento_unico(Cliente, 'bi_passaporte', cliente.bi_passaporte, request.user, cliente.id)
            if not is_unique:
                messages.error(request, error)
                return render(request, 'clientes/formulario.html', {'cliente': cliente})

        # Processar renda
        try:
            cliente.renda_mensal = float(renda_raw) if renda_raw else None
        except ValueError:
            messages.error(request, 'Renda mensal inválida.')
            return render(request, 'clientes/formulario.html', {'cliente': cliente})

        # Salvar
        try:
            cliente.save()
            messages.success(request, f'Cliente "{cliente.nome}" atualizado com sucesso!')
            logger.info(f"Cliente atualizado: {cliente.id} - {cliente.nome}")
            return redirect('clientes')
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente: {e}")
            messages.error(request, 'Erro ao atualizar cliente. Tente novamente.')
            return render(request, 'clientes/formulario.html', {'cliente': cliente})

    return render(request, 'clientes/formulario.html', {'cliente': cliente})


@login_required
@verificar_assinatura
def cliente_excluir(request, id):
    """Excluir cliente com verificação de empréstimos associados"""
    cliente = get_object_or_404(Cliente, id=id, usuario=request.user)
    nome = cliente.nome
    
    # Verificar se o cliente tem empréstimos
    if cliente.emprestimos.exists():
        messages.warning(
            request,
            f'O cliente "{nome}" possui {cliente.emprestimos.count()} empréstimo(s) associado(s). '
            'Exclua os empréstimos primeiro ou regularize a situação.'
        )
        return redirect('clientes')
    
    try:
        cliente.delete()
        messages.success(request, f'Cliente "{nome}" excluído com sucesso!')
        logger.info(f"Cliente excluído: {id} - {nome}")
    except Exception as e:
        logger.error(f"Erro ao excluir cliente {id}: {e}")
        messages.error(request, 'Erro ao excluir cliente. Tente novamente.')
    
    return redirect('clientes')


# ============================================
# API PARA VALIDAÇÃO DE DOCUMENTOS EM TEMPO REAL
# ============================================

@login_required
@require_http_methods(["POST"])
def validar_documento_api(request):
    """
    API para validar documentos em tempo real (AJAX)
    """
    try:
        data = json.loads(request.body)
        campo = data.get('campo')
        valor = data.get('valor', '').strip()
        
        if not campo or not valor:
            return JsonResponse({'valid': False, 'error': 'Campo ou valor não informado'})
        
        resultado = {'valid': True, 'message': '', 'tipo': None}
        
        if campo == 'nuit':
            valid, error = validar_nuit(valor)
            resultado['valid'] = valid
            resultado['message'] = error if not valid else 'NUIT válido'
            
            if valid and valor:
                is_unique, _ = verificar_documento_unico(Cliente, 'nuit', valor, request.user)
                if not is_unique:
                    resultado['valid'] = False
                    resultado['message'] = 'NUIT já cadastrado para outro cliente'
        
        elif campo == 'nuib':
            valid, error = validar_nuib(valor)
            resultado['valid'] = valid
            resultado['message'] = error if not valid else 'NUIB válido'
            
            if valid and valor:
                is_unique, _ = verificar_documento_unico(Cliente, 'nuib', valor, request.user)
                if not is_unique:
                    resultado['valid'] = False
                    resultado['message'] = 'NUIB já cadastrado para outro cliente'
        
        elif campo == 'bi_passaporte':
            valid, error, tipo = validar_bi_passaporte(valor)
            resultado['valid'] = valid
            resultado['message'] = error if not valid else f'Documento válido: {tipo}'
            resultado['tipo'] = tipo
            
            if valid and valor:
                is_unique, _ = verificar_documento_unico(Cliente, 'bi_passaporte', valor, request.user)
                if not is_unique:
                    resultado['valid'] = False
                    resultado['message'] = 'BI/Passaporte já cadastrado para outro cliente'
        
        else:
            return JsonResponse({'valid': False, 'error': 'Campo inválido'})
        
        return JsonResponse(resultado)
        
    except Exception as e:
        logger.error(f"Erro na API de validação: {e}")
        return JsonResponse({'valid': False, 'error': 'Erro interno'}, status=500)


# ============================================
# EMPRÉSTIMOS
# ============================================

@login_required
@verificar_assinatura
def lista_emprestimos(request):
    emprestimos = Emprestimo.objects.filter(usuario=request.user).select_related('cliente')
    clientes = Cliente.objects.filter(usuario=request.user)

    status = request.GET.get('status')
    cliente_id = request.GET.get('cliente')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if status:
        emprestimos = emprestimos.filter(status=status)
    if cliente_id:
        emprestimos = emprestimos.filter(cliente_id=cliente_id)
    if data_inicio:
        emprestimos = emprestimos.filter(data_contrato__gte=data_inicio)
    if data_fim:
        emprestimos = emprestimos.filter(data_contrato__lte=data_fim)

    return render(request, 'emprestimo/lista.html', {'emprestimos': emprestimos, 'clientes': clientes})


@login_required
@verificar_assinatura
def emprestimo_cadastrar(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        valor = request.POST.get('valor')
        taxa_juros = request.POST.get('taxa_juros')
        quantidade_parcelas = request.POST.get('quantidade_parcelas')
        data_primeiro_vencimento = request.POST.get('data_primeiro_vencimento')
        tipo_juros = request.POST.get('tipo_juros')

        if not all([cliente_id, valor, taxa_juros, quantidade_parcelas, data_primeiro_vencimento]):
            messages.error(request, 'Todos os campos são obrigatórios.')
            clientes = Cliente.objects.filter(usuario=request.user)
            return render(request, 'emprestimo/formulario.html', {'clientes': clientes})

        cliente = get_object_or_404(Cliente, id=cliente_id, usuario=request.user)

        try:
            valor_limpo = valor.replace('.', '').replace(',', '.')
            valor_float = float(valor_limpo)
            taxa_juros_float = float(taxa_juros)
            quantidade_parcelas_int = int(quantidade_parcelas)
            data_vencimento = datetime.strptime(data_primeiro_vencimento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Verifique os valores informados (valor, taxa, parcelas ou data).')
            clientes = Cliente.objects.filter(usuario=request.user)
            return render(request, 'emprestimo/formulario.html', {'clientes': clientes})

        emprestimo = Emprestimo.objects.create(
            usuario=request.user,
            cliente=cliente,
            valor=valor_float,
            taxa_juros=taxa_juros_float,
            quantidade_parcelas=quantidade_parcelas_int,
            data_primeiro_vencimento=data_vencimento,
            tipo_juros=tipo_juros,
            status='ativo',
        )

        gerar_parcelas(emprestimo)

        messages.success(request, f'Empréstimo de {cliente.nome} cadastrado com sucesso!')
        return redirect('emprestimo')

    clientes = Cliente.objects.filter(usuario=request.user)
    return render(request, 'emprestimo/formulario.html', {'clientes': clientes})


def gerar_parcelas(emprestimo):
    data_vencimento = emprestimo.data_primeiro_vencimento
    for i in range(1, emprestimo.quantidade_parcelas + 1):
        Parcela.objects.create(
            emprestimo=emprestimo,
            numero=i,
            valor=emprestimo.valor_parcela,
            data_vencimento=data_vencimento,
            status='pendente',
        )
        data_vencimento += timedelta(days=30)


@login_required
@verificar_assinatura
def emprestimo_parcelas(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id, usuario=request.user)
    parcelas = emprestimo.parcelas.all()
    return render(request, 'emprestimo/parcelas.html', {'emprestimo': emprestimo, 'parcelas': parcelas})


@login_required
@require_http_methods(["POST"])
def emprestimo_baixar_api(request, id):
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if not funcionario.pode_baixar_emprestimos and funcionario.cargo != 'admin_empresa':
            return JsonResponse(
                {'success': False, 'error': 'Você não tem permissão para baixar empréstimos.'},
                status=403,
            )

    emprestimo = get_object_or_404(Emprestimo, id=id, usuario=request.user)

    if emprestimo.status == 'pago':
        return JsonResponse({'success': False, 'error': 'Empréstimo já está pago.'})

    emprestimo.status = 'pago'
    emprestimo.save()

    emprestimo.parcelas.update(status='pago', data_pagamento=timezone.now().date())

    return JsonResponse({'success': True, 'message': 'Empréstimo baixado com sucesso!'})


# ============================================
# PAGAMENTOS
# ============================================

@login_required
@verificar_assinatura
def pagamento(request):
    usuario = request.user
    hoje = date.today()

    parcelas_pendentes = Parcela.objects.filter(
        emprestimo__usuario=usuario,
        status='pendente',
        data_vencimento__gte=hoje
    ).select_related('emprestimo__cliente').order_by('data_vencimento')

    pendentes_lista = []
    for p in parcelas_pendentes:
        dias_restantes = (p.data_vencimento - hoje).days
        pendentes_lista.append({
            'id': p.id,
            'cliente_nome': p.emprestimo.cliente.nome,
            'cliente_telefone': p.emprestimo.cliente.telefone,
            'emprestimo_id': p.emprestimo.id,
            'numero': p.numero,
            'total_parcelas': p.emprestimo.quantidade_parcelas,
            'valor': float(p.valor),
            'valor_str': str(float(p.valor)).replace('.', ','),
            'data_vencimento': p.data_vencimento,
            'dias_restantes': dias_restantes,
        })

    parcelas_atrasadas = Parcela.objects.filter(
        emprestimo__usuario=usuario,
        status='pendente',
        data_vencimento__lt=hoje
    ).select_related('emprestimo__cliente').order_by('data_vencimento')

    atrasadas_lista = []
    for p in parcelas_atrasadas:
        dias_atraso = (hoje - p.data_vencimento).days
        multa = p.valor * Decimal('0.02')
        juros = p.valor * Decimal('0.00033') * dias_atraso
        valor_total = p.valor + multa + juros

        atrasadas_lista.append({
            'id': p.id,
            'cliente_nome': p.emprestimo.cliente.nome,
            'cliente_telefone': p.emprestimo.cliente.telefone,
            'emprestimo_id': p.emprestimo.id,
            'numero': p.numero,
            'total_parcelas': p.emprestimo.quantidade_parcelas,
            'valor_original': float(p.valor),
            'multa': float(multa),
            'juros': float(juros),
            'valor_total': float(valor_total),
            'valor_total_str': str(float(valor_total)).replace('.', ','),
            'data_vencimento': p.data_vencimento,
            'dias_atraso': dias_atraso,
        })

    historico_pagamentos = Pagamento.objects.filter(
        parcela__emprestimo__usuario=usuario
    ).select_related('parcela__emprestimo__cliente').order_by('-data_pagamento')[:50]

    historico_lista = []
    for pag in historico_pagamentos:
        historico_lista.append({
            'id': pag.id,
            'data': pag.data_pagamento,
            'cliente_nome': pag.parcela.emprestimo.cliente.nome,
            'emprestimo_id': pag.parcela.emprestimo.id,
            'parcela_numero': pag.parcela.numero,
            'total_parcelas': pag.parcela.emprestimo.quantidade_parcelas,
            'valor': float(pag.valor),
            'forma_pagamento': pag.forma_pagamento,
            'get_forma_pagamento_display': dict(Pagamento.FORMA_CHOICES).get(pag.forma_pagamento, pag.forma_pagamento),
            'comprovante': pag.comprovante.url if pag.comprovante else None,
        })

    inicio_mes = datetime(hoje.year, hoje.month, 1).date()
    recebido_mes = Pagamento.objects.filter(
        parcela__emprestimo__usuario=usuario,
        data_pagamento__date__gte=inicio_mes
    ).aggregate(Sum('valor'))['valor__sum'] or 0

    a_receber = Parcela.objects.filter(
        emprestimo__usuario=usuario,
        status='pendente',
        data_vencimento__gte=hoje
    ).aggregate(Sum('valor'))['valor__sum'] or 0

    em_atraso_total = Decimal('0')
    for p in parcelas_atrasadas:
        dias = (hoje - p.data_vencimento).days
        multa = p.valor * Decimal('0.02')
        juros = p.valor * Decimal('0.00033') * dias
        em_atraso_total += (p.valor + multa + juros)

    context = {
        'recebido_mes': float(recebido_mes),
        'a_receber': float(a_receber),
        'em_atraso': float(em_atraso_total),
        'parcelas_pendentes': pendentes_lista,
        'parcelas_atrasadas': atrasadas_lista,
        'historico_pagamentos': historico_lista,
    }

    return render(request, 'pagamentos/lista.html', context)


@login_required
@require_http_methods(["POST"])
def registrar_pagamento(request):
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if not funcionario.pode_regularizar_parcelas and funcionario.cargo != 'admin_empresa':
            return JsonResponse(
                {'success': False, 'error': 'Você não tem permissão para regularizar parcelas.'},
                status=403,
            )

    try:
        parcela_id = request.POST.get('parcela_id')
        valor = request.POST.get('valor')
        forma_pagamento = request.POST.get('forma_pagamento')
        comprovante = request.FILES.get('comprovante')

        logger.info(
            "registrar_pagamento: user=%s parcela_id=%s valor=%s forma=%s",
            request.user.pk, parcela_id, valor, forma_pagamento,
        )

        if not parcela_id:
            return JsonResponse({'success': False, 'error': 'ID da parcela não informado'})

        if not valor:
            return JsonResponse({'success': False, 'error': 'Valor não informado'})

        if not forma_pagamento:
            return JsonResponse({'success': False, 'error': 'Forma de pagamento não informada'})

        try:
            valor_float = float(valor)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Valor inválido'})

        parcela = Parcela.objects.get(id=parcela_id, emprestimo__usuario=request.user)

        if parcela.status == 'pago':
            return JsonResponse({'success': False, 'error': 'Esta parcela já foi paga'})

        pagamento = Pagamento.objects.create(
            parcela=parcela,
            valor=valor_float,
            forma_pagamento=forma_pagamento,
            comprovante=comprovante,
        )

        parcela.status = 'pago'
        parcela.data_pagamento = timezone.now().date()
        parcela.save()

        logger.info("Pagamento criado com sucesso: id=%s", pagamento.id)

        return JsonResponse({
            'success': True,
            'message': f'Pagamento de MT {valor_float:.2f} registrado com sucesso!',
            'pagamento_id': pagamento.id,
        })

    except Parcela.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Parcela não encontrada'})

    except Exception as e:
        logger.error("Erro inesperado em registrar_pagamento: %s", e)
        return JsonResponse({'success': False, 'error': 'Erro interno ao registrar pagamento.'})


@login_required
@verificar_assinatura
def simular_juros(request, parcela_id):
    try:
        parcela = Parcela.objects.get(id=parcela_id, emprestimo__usuario=request.user)
        hoje = date.today()

        if parcela.data_vencimento >= hoje:
            return JsonResponse({
                'valor_original': float(parcela.valor),
                'dias_atraso': 0,
                'multa': 0,
                'juros_mora': 0,
                'valor_total': float(parcela.valor),
            })

        dias_atraso = (hoje - parcela.data_vencimento).days
        multa = float(parcela.valor * Decimal('0.02'))
        juros_mora = float(parcela.valor * Decimal('0.00033') * dias_atraso)
        valor_total = float(parcela.valor) + multa + juros_mora

        return JsonResponse({
            'valor_original': float(parcela.valor),
            'dias_atraso': dias_atraso,
            'multa': multa,
            'juros_mora': juros_mora,
            'valor_total': valor_total,
        })
    except Parcela.DoesNotExist:
        return JsonResponse({'error': 'Parcela não encontrada'}, status=404)
    except Exception as e:
        logger.error("Erro em simular_juros: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


# ============================================
# RELATÓRIOS
# ============================================

@login_required
@verificar_assinatura
def relatorios(request):
    usuario = request.user
    hoje = date.today()

    total_clientes = Cliente.objects.filter(usuario=usuario).count()
    total_emprestimos = Emprestimo.objects.filter(usuario=usuario).count()
    valor_total_emprestado = Emprestimo.objects.filter(usuario=usuario).aggregate(Sum('valor'))['valor__sum'] or 0

    status_data = Emprestimo.objects.filter(usuario=usuario).values('status').annotate(total=Count('id'))
    status_labels = [dict(Emprestimo.STATUS_CHOICES).get(s['status'], s['status']) for s in status_data]
    status_values = [s['total'] for s in status_data]

    top_clientes = Cliente.objects.filter(
        usuario=usuario,
        emprestimos__isnull=False
    ).annotate(
        total_emprestimos=Count('emprestimos'),
        valor_total=Sum('emprestimos__valor')
    ).order_by('-valor_total')[:5]

    resumo_status = []
    total_valor = Emprestimo.objects.filter(usuario=usuario).aggregate(Sum('valor'))['valor__sum'] or 0
    for status_code, status_name in Emprestimo.STATUS_CHOICES:
        qs = Emprestimo.objects.filter(usuario=usuario, status=status_code)
        total = qs.count()
        valor = qs.aggregate(Sum('valor'))['valor__sum'] or 0
        percentual = (valor / total_valor * 100) if total_valor > 0 else 0
        resumo_status.append({
            'status': status_code,
            'get_status_display': status_name,
            'total': total,
            'valor': valor,
            'percentual': round(percentual, 1),
        })

    monthly_labels = []
    monthly_data = []
    for i in range(5, -1, -1):
        data = hoje - timedelta(days=30 * i)
        monthly_labels.append(data.strftime('%b/%Y'))
        total = Emprestimo.objects.filter(
            usuario=usuario,
            data_contrato__year=data.year,
            data_contrato__month=data.month
        ).aggregate(Sum('valor'))['valor__sum'] or 0
        monthly_data.append(float(total))

    parcelas_atrasadas = Parcela.objects.filter(
        emprestimo__usuario=usuario,
        status='pendente',
        data_vencimento__lt=hoje
    ).count()
    total_parcelas = Parcela.objects.filter(emprestimo__usuario=usuario).count()
    taxa_inadimplencia = (parcelas_atrasadas / total_parcelas * 100) if total_parcelas > 0 else 0

    # Histórico de pagamentos - para constar no relatório físico (PDF)
    historico_pagamentos = Pagamento.objects.filter(
        parcela__emprestimo__usuario=usuario
    ).select_related('parcela__emprestimo__cliente').order_by('-data_pagamento')[:100]

    historico_lista = []
    for pag in historico_pagamentos:
        historico_lista.append({
            'id': pag.id,
            'data': pag.data_pagamento,
            'cliente_nome': pag.parcela.emprestimo.cliente.nome,
            'emprestimo_id': pag.parcela.emprestimo.id,
            'parcela_numero': pag.parcela.numero,
            'total_parcelas': pag.parcela.emprestimo.quantidade_parcelas,
            'valor': float(pag.valor),
            'forma_pagamento': pag.forma_pagamento,
            'get_forma_pagamento_display': dict(Pagamento.FORMA_CHOICES).get(pag.forma_pagamento, pag.forma_pagamento),
        })

    context = {
        'total_clientes': total_clientes,
        'total_emprestimos': total_emprestimos,
        'valor_total_emprestado': valor_total_emprestado,
        'taxa_inadimplencia': round(taxa_inadimplencia, 1),
        'status_labels': status_labels,
        'status_data': status_values,
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'top_clientes': top_clientes,
        'resumo_status': resumo_status,
        'historico_pagamentos': historico_lista,
    }

    return render(request, 'relatorio/geral.html', context)

#===============================================================================
@login_required
def pagar_parcela(request, parcela_id):
    parcela = get_object_or_404(Parcela, id=parcela_id, emprestimo__usuario=request.user)

    if request.method == 'POST':
        forma_pagamento = request.POST.get('forma_pagamento')
        comprovante = request.FILES.get('comprovante')
        observacoes = request.POST.get('observacoes', '')

        if not forma_pagamento:
            messages.error(request, 'Selecione a forma de pagamento.')
            return render(request, 'pagamentos/pagar.html', {'parcela': parcela})

        Pagamento.objects.create(
            parcela=parcela,
            valor=parcela.valor,
            forma_pagamento=forma_pagamento,
            comprovante=comprovante,
            observacoes=observacoes,
        )

        messages.success(request, f'Pagamento da parcela {parcela.numero} registrado com sucesso!')
        return redirect('pagamentos')

    return render(request, 'pagamentos/pagar.html', {'parcela': parcela})


@login_required
def regularizar_parcela(request, parcela_id):
    parcela = get_object_or_404(Parcela, id=parcela_id, emprestimo__usuario=request.user)
    hoje = date.today()
    dias_atraso = (hoje - parcela.data_vencimento).days

    multa = parcela.valor * Decimal('0.02')
    juros = parcela.valor * Decimal('0.00033') * dias_atraso
    valor_total = parcela.valor + multa + juros

    if request.method == 'POST':
        forma_pagamento = request.POST.get('forma_pagamento')
        comprovante = request.FILES.get('comprovante')
        observacoes = request.POST.get('observacoes', '')

        if not forma_pagamento:
            messages.error(request, 'Selecione a forma de pagamento.')
            return render(request, 'pagamentos/regularizar.html', {
                'parcela': parcela,
                'dias_atraso': dias_atraso,
                'multa': multa,
                'juros': juros,
                'valor_total': valor_total,
            })

        Pagamento.objects.create(
            parcela=parcela,
            valor=valor_total,
            forma_pagamento=forma_pagamento,
            comprovante=comprovante,
            observacoes=observacoes,
        )

        messages.success(request, f'Pagamento da parcela {parcela.numero} regularizado com sucesso!')
        return redirect('pagamentos')

    return render(request, 'pagamentos/regularizar.html', {
        'parcela': parcela,
        'dias_atraso': dias_atraso,
        'multa': multa,
        'juros': juros,
        'valor_total': valor_total,
    })


# ============================================
# EMPRESA / CONFIGURAÇÕES
# ============================================

@login_required
def empresa_config(request):
    empresa, created = Empresa.objects.get_or_create(
        user=request.user,
        defaults={
            'nome': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'status': 'ativa',
        }
    )

    if request.method == 'POST':
        empresa.nome = request.POST.get('nome')
        empresa.telefone = request.POST.get('telefone')
        empresa.email = request.POST.get('email')
        empresa.endereco = request.POST.get('endereco')
        empresa.status = request.POST.get('status')

        if request.FILES.get('logo'):
            empresa.logo = request.FILES.get('logo')

        empresa.save()
        messages.success(request, 'Dados da empresa salvos com sucesso!')
        return redirect('empresa_config')

    return render(request, 'empresa/config.html', {'empresa': empresa})


@login_required
def config_notificacoes(request):
    try:
        empresa = Empresa.objects.get(user=request.user)
        config, created = ConfiguracaoNotificacao.objects.get_or_create(empresa=empresa)
    except Empresa.DoesNotExist:
        messages.error(request, 'Configure primeiro os dados da sua empresa.')
        return redirect('empresa_config')

    if request.method == 'POST':
        config.whatsapp_token = request.POST.get('whatsapp_token')
        config.whatsapp_phone_id = request.POST.get('whatsapp_phone_id')
        config.sms_api_key = request.POST.get('sms_api_key')
        config.notificar_vencimento = request.POST.get('notificar_vencimento') == 'on'
        config.notificar_atraso = request.POST.get('notificar_atraso') == 'on'

        try:
            config.dias_antecedencia = int(request.POST.get('dias_antecedencia', 5))
            config.atraso_frequencia = int(request.POST.get('atraso_frequencia', 2))
            config.push_dias_antecedencia = int(request.POST.get('push_dias_antecedencia', 3))
        except ValueError:
            messages.error(request, 'Verifique os valores numéricos informados.')
            return render(request, 'empresa/config_notificacoes.html', {'config': config})

        config.push_notificacoes_ativas = request.POST.get('push_notificacoes_ativas') == 'on'
        config.push_alertar_vencimento = request.POST.get('push_alertar_vencimento') == 'on'
        config.push_alertar_atraso = request.POST.get('push_alertar_atraso') == 'on'

        horario_inicio = request.POST.get('push_horario_inicio')
        horario_fim = request.POST.get('push_horario_fim')
        try:
            if horario_inicio:
                config.push_horario_inicio = datetime.strptime(horario_inicio, '%H:%M').time()
            if horario_fim:
                config.push_horario_fim = datetime.strptime(horario_fim, '%H:%M').time()
        except ValueError:
            messages.error(request, 'Horário inválido. Use o formato HH:MM.')
            return render(request, 'empresa/config_notificacoes.html', {'config': config})

        config.save()

        messages.success(request, 'Configurações de notificação salvas com sucesso!')
        return redirect('config_notificacoes')

    return render(request, 'empresa/config_notificacoes.html', {'config': config})


# ============================================
# NOTIFICAÇÕES PUSH
# ============================================

@login_required
@csrf_exempt
@require_http_methods(['POST'])
def inscrever_push(request):
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')

        if not subscription:
            return JsonResponse({'error': 'Subscription não fornecida'}, status=400)

        PushSubscription.objects.filter(usuario=request.user).delete()

        obj = PushSubscription.objects.create(
            usuario=request.user,
            subscription_info=subscription,
            is_active=True,
        )

        logger.info("Nova inscrição push criada: id=%s user=%s", obj.id, request.user.pk)
        return JsonResponse({'success': True, 'created': True})

    except Exception as e:
        logger.error("Erro em inscrever_push: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


@login_required
def verificar_inscricao_push(request):
    has_subscription = PushSubscription.objects.filter(
        usuario=request.user,
        is_active=True
    ).exists()

    return JsonResponse({'has_subscription': has_subscription})


@login_required
@require_http_methods(['POST'])
def desinscrever_push(request):
    try:
        PushSubscription.objects.filter(usuario=request.user).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error("Erro em desinscrever_push: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_fcm_device(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuário não autenticado'}, status=401)

    try:
        data = json.loads(request.body)
        token = data.get('registration_id')

        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=400)

        device, created = FCMDevice.objects.get_or_create(
            registration_id=token,
            defaults={
                'user': request.user,
                'type': 'web',
                'active': True,
            }
        )

        if not created:
            device.user = request.user
            device.active = True
            device.save()

        return JsonResponse({
            'success': True,
            'message': 'Dispositivo registrado com sucesso',
        })

    except Exception as e:
        logger.error("Erro em register_fcm_device: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


# ============================================
# GERENCIAMENTO DE FUNCIONÁRIOS
# ============================================

@login_required
def gerenciar_funcionarios(request):
    if not hasattr(request.user, 'empresa'):
        messages.error(request, 'Você não possui uma empresa associada.')
        return redirect('dashboard')

    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if funcionario.cargo != 'admin_empresa':
            messages.error(request, 'Apenas administradores podem gerenciar funcionários.')
            return redirect('dashboard')

    funcionarios = Funcionario.objects.filter(empresa=request.user.empresa)

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cargo = request.POST.get('cargo')

        if username and email and password:
            try:
                validate_password(password)
            except ValidationError as e:
                for erro in e.messages:
                    messages.error(request, erro)
                return redirect('gerenciar_funcionarios')

            user = User.objects.create_user(username=username, email=email, password=password)
            Funcionario.objects.create(
                usuario=user,
                empresa=request.user.empresa,
                cargo=cargo,
                pode_baixar_emprestimos=request.POST.get('pode_baixar') == 'on',
                pode_regularizar_parcelas=request.POST.get('pode_regularizar') == 'on',
                pode_configurar_empresa=request.POST.get('pode_configurar') == 'on',
                ativo=True,
            )
            messages.success(request, f'Funcionário {username} criado com sucesso!')
        return redirect('gerenciar_funcionarios')

    return render(request, 'funcionarios/gerenciar.html', {'funcionarios': funcionarios})


# ============================================
# PAINEL ADMINISTRATIVO - EMPRESAS E FACTURAÇÃO
# ============================================

@login_required
def admin_lista_empresas(request):
    """Lista todas as empresas cadastradas na plataforma, com plano assinado e total já facturado (apenas superusuários)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acesso restrito a administradores da plataforma.')
        return redirect('dashboard')

    empresas = Empresa.objects.select_related('user').all().order_by('nome')

    empresas_lista = []
    for empresa in empresas:
        try:
            assinatura = Assinatura.objects.select_related('plano').get(usuario=empresa.user)
            plano_nome = assinatura.plano.get_nome_display() if assinatura.plano else 'Sem plano'
            status_assinatura = assinatura.get_status_display()
            data_expiracao = assinatura.data_expiracao
        except Assinatura.DoesNotExist:
            plano_nome = 'Sem plano'
            status_assinatura = 'Sem assinatura'
            data_expiracao = None

        total_facturado = TransacaoMPESA.objects.filter(
            usuario=empresa.user,
            status='sucesso'
        ).aggregate(Sum('valor'))['valor__sum'] or 0

        empresas_lista.append({
            'id': empresa.id,
            'nome': empresa.nome,
            'email': empresa.email,
            'telefone': empresa.telefone,
            'status_empresa': empresa.get_status_display(),
            'plano_nome': plano_nome,
            'status_assinatura': status_assinatura,
            'data_expiracao': data_expiracao,
            'total_facturado': float(total_facturado),
        })

    return render(request, 'admin_painel/lista_empresas.html', {'empresas': empresas_lista})


@login_required
def admin_relatorio_empresa_pdf(request, empresa_id):
    """
    Gera um relatório PDF com as transações de assinatura (M-Pesa/e-Mola) de uma
    empresa, referentes a um mês específico. Acessível pelo superusuário da
    plataforma ou pela própria empresa (para partilhar com os seus parceiros).
    """
    empresa = get_object_or_404(Empresa, id=empresa_id)

    if not (request.user.is_superuser or request.user == empresa.user):
        messages.error(request, 'Você não tem permissão para acessar este relatório.')
        return redirect('dashboard')

    hoje = date.today()
    try:
        ano = int(request.GET.get('ano', hoje.year))
        mes = int(request.GET.get('mes', hoje.month))
    except ValueError:
        ano = hoje.year
        mes = hoje.month

    transacoes = TransacaoMPESA.objects.filter(
        usuario=empresa.user,
        status='sucesso',
        data_criacao__year=ano,
        data_criacao__month=mes,
    ).order_by('data_criacao')

    total_mes = transacoes.aggregate(Sum('valor'))['valor__sum'] or 0

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    meses_pt = [
        '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]

    y = altura - 50
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(50, y, 'CODE-MIND - Relatório de Facturação Mensal')

    y -= 30
    pdf.setFont('Helvetica', 11)
    pdf.drawString(50, y, f'Empresa: {empresa.nome}')
    y -= 18
    pdf.drawString(50, y, f'Período: {meses_pt[mes]} de {ano}')
    y -= 18
    pdf.drawString(50, y, f'Gerado em: {timezone.now().strftime("%d/%m/%Y %H:%M")}')

    y -= 35
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(50, y, 'Data')
    pdf.drawString(150, y, 'Referência')
    pdf.drawString(320, y, 'Telefone')
    pdf.drawString(420, y, 'Valor (MT)')
    y -= 5
    pdf.line(50, y, 545, y)
    y -= 15

    pdf.setFont('Helvetica', 9)
    if not transacoes.exists():
        pdf.drawString(50, y, 'Nenhuma transação registada neste período.')
        y -= 16
    else:
        for t in transacoes:
            if y < 60:
                pdf.showPage()
                y = altura - 50
                pdf.setFont('Helvetica', 9)

            pdf.drawString(50, y, t.data_criacao.strftime('%d/%m/%Y %H:%M'))
            pdf.drawString(150, y, t.referencia)
            pdf.drawString(320, y, t.telefone)
            pdf.drawString(420, y, f'{t.valor:.2f}')
            y -= 16

    y -= 10
    pdf.line(50, y, 545, y)
    y -= 20
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, f'Total facturado no mês: {total_mes:.2f} MT')
    y -= 16
    pdf.setFont('Helvetica', 9)
    pdf.drawString(50, y, f'Número de transações: {transacoes.count()}')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    nome_arquivo = f'relatorio_{empresa.nome.replace(" ", "_")}_{mes:02d}_{ano}.pdf'
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    return response


# ============================================
# PÁGINAS LEGAIS
# ============================================

def termos_e_condicoes(request):
    return render(request, 'legal/termos_e_condicoes.html')


def politica_privacidade(request):
    return render(request, 'legal/politica_privacidade.html')

