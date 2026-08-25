import logging
import hmac
import hashlib
import json
import re
import uuid
import secrets
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
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from fcm_django.models import FCMDevice

from .models import (
    Parcela, Pagamento, Emprestimo, Cliente,
    Assinatura, Plano, PagamentoAssinatura, TransacaoMPESA,
    Empresa, PushSubscription, EmailVerificacao,
    ConfiguracaoNotificacao, Funcionario,
)
from .mpesa_service import NetShopService
from .forms import CadastroForm, LoginForm

logger = logging.getLogger('django')

# Dominios de e-mail temporario/descartavel bloqueados no cadastro
DOMINIOS_EMAIL_BLOQUEADOS = [
    'temp-mail.com', 'mailinator.com', 'guerrillamail.com',
    '10minutemail.com', 'throwawaymail.com', 'yopmail.com',
    'fakeinbox.com', 'mailnator.com', 'getairmail.com',
    'sharklasers.com', 'guerrillamail.net', 'guerrillamail.org',
    'mailmetrash.com', 'trashmail.com', 'tempemail.net',
    'tempmail.com', 'mohmal.com', 'dispostable.com',
]

# ============================================
# PAGINAS PUBLICAS
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

            # Mensagem generica: mensagens diferentes para "email nao
            # existe" e "senha errada" permitem enumerar quais e-mails
            # estao cadastrados na base.
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
            messages.error(request, 'E-mail e obrigatorio.')
            return render(request, 'auth/cadastro.html')

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            messages.error(request, 'Digite um e-mail valido (exemplo: nome@dominio.com)')
            return render(request, 'auth/cadastro.html')

        dominio = email.split('@')[1].lower()
        if dominio in DOMINIOS_EMAIL_BLOQUEADOS:
            messages.error(request, 'Nao e permitido usar e-mails temporarios ou descartaveis.')
            return render(request, 'auth/cadastro.html')

        try:
            dns.resolver.resolve(dominio, 'MX')
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers) as e:
            logger.warning("Dominio de e-mail sem MX valido no cadastro: %s (%s)", dominio, e)
        except dns.exception.Timeout:
            logger.warning("Timeout ao validar MX do dominio: %s", dominio)

        if not termos:
            messages.error(request, 'Voce deve aceitar os termos de uso.')
            return render(request, 'auth/cadastro.html')

        if not first_name or not last_name:
            messages.error(request, 'Nome e sobrenome sao obrigatorios.')
            return render(request, 'auth/cadastro.html')

        if not telefone:
            messages.error(request, 'Telefone e obrigatorio.')
            return render(request, 'auth/cadastro.html')

        if senha1 != senha2:
            messages.error(request, 'As senhas nao conferem.')
            return render(request, 'auth/cadastro.html')

        try:
            validate_password(senha1)
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return render(request, 'auth/cadastro.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail ja esta cadastrado.')
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
                        f'Ola {first_name}!\n\n'
                        f'Obrigado por se cadastrar na CODE-MIND.\n\n'
                        f'Para ativar sua conta e comecar a usar o sistema, clique no link abaixo:\n\n'
                        f'{link}\n\n'
                        f'Este link e valido por 24 horas.\n\n'
                        f'Se voce nao solicitou este cadastro, ignore este email.\n\n'
                        f'Atenciosamente,\nEquipe CODE-MIND'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f'Cadastro realizado, {first_name}! Enviamos um link de confirmacao '
                    f'para seu email. Verifique sua caixa de entrada.'
                )
            except Exception as e:
                logger.error("Erro ao enviar email de confirmacao para %s: %s", email, e)
                messages.warning(
                    request,
                    'Cadastro realizado, mas houve erro ao enviar email de confirmacao. '
                    'Entre em contato com o suporte.'
                )

            return redirect('login')

        except Exception as e:
            logger.error("Erro ao criar conta para %s: %s", email, e)
            messages.error(request, 'Erro ao criar conta. Tente novamente.')
            return render(request, 'auth/cadastro.html')

    return render(request, 'auth/cadastro.html')


def confirmar_email_view(request, codigo):
    """Confirma o email do usuario e ativa a conta"""
    try:
        verificacao = EmailVerificacao.objects.get(codigo=codigo)

        if verificacao.verificado_em:
            messages.warning(request, 'Este email ja foi verificado. Faca login.')
            return redirect('login')

        if timezone.now() > verificacao.expira_em:
            messages.error(request, 'Este link de confirmacao expirou. Solicite um novo.')
            return redirect('login')

        user = verificacao.usuario
        user.is_active = True
        user.save()

        verificacao.verificado_em = timezone.now()
        verificacao.save()

        messages.success(request, 'Email confirmado! Agora voce pode fazer login.')
        return redirect('login')

    except EmailVerificacao.DoesNotExist:
        messages.error(request, 'Link de confirmacao invalido.')
        return redirect('login')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('inicio')


# ============================================
# DECORATOR PARA VERIFICAR ASSINATURA
# ============================================
def verificar_assinatura(view_func):
    """Decorator para verificar se o usuario tem assinatura ativa (admin tem acesso total)"""
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
# PAGINAS PROTEGIDAS (requerem assinatura ativa)
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
        messages.error(request, 'Plano nao encontrado.')
        return redirect('planos')

    return redirect('pagamento_mpesa', plano_nome=plano_nome)

#=================================================================
@login_required
def pagamento_mpesa(request, plano_nome):
    try:
        plano = Plano.objects.get(nome=plano_nome)
    except Plano.DoesNotExist:
        messages.error(request, 'Plano nao encontrado.')
        return redirect('planos')

    if request.method == 'GET':
        return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})

    if request.method == 'POST':
        metodo = request.POST.get('metodo_pagamento', 'emola')
        telefone = request.POST.get('telefone', '').strip()

        if metodo in ('mpesa', 'emola', 'mkesh') and not telefone:
            messages.error(request, 'Informe o numero de telefone para pagamentos via M-Pesa/e-Mola.')
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
            messages.info(request, 'Pagamento iniciado. Confirme no seu telemovel.')
            return redirect('pagamento_mpesa_status', transacao_id=transacao.id)

    return JsonResponse({'error': 'Metodo nao permitido'}, status=405)

#=================================================================================================
@login_required
def pagamento_mpesa_status(request, transacao_id):
    """Verificar status do pagamento"""
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
            messages.info(request, 'Pagamento ainda em processamento. Aguarde a confirmacao.')

    return render(request, 'planos/status_mpesa.html', {'transacao': transacao})

#=========================================================================================
@csrf_exempt
def mpesa_callback(request):
    """
    Webhook para receber callbacks do PaySuite.

    IMPORTANTE: valida a assinatura HMAC do payload contra
    settings.PAYSUITE_WEBHOOK_SECRET antes de processar qualquer coisa.
    Sem essa validacao, qualquer pessoa poderia forjar um POST simulando
    pagamento bem-sucedido e ativar assinaturas de graca.

    Confirme na documentacao do PaySuite qual e o nome exato do header
    de assinatura e o algoritmo usado (aqui assumimos HMAC-SHA256 num
    header 'X-PaySuite-Signature' -- ajuste conforme a doc real deles).
    """
    if request.method != 'POST':
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Method not allowed'})

    assinatura_recebida = request.headers.get('X-PaySuite-Signature', '')
    webhook_secret = getattr(settings, 'PAYSUITE_WEBHOOK_SECRET', '')

    if not webhook_secret:
        logger.error("PAYSUITE_WEBHOOK_SECRET nao configurado -- recusando webhook.")
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Server misconfigured'}, status=500)

    assinatura_esperada = hmac.new(
        webhook_secret.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(assinatura_recebida, assinatura_esperada):
        logger.warning("Webhook PaySuite recebido com assinatura invalida ou ausente.")
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
    """Ativar assinatura do usuario apos pagamento confirmado"""
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
    """
    Simula um callback de pagamento bem-sucedido -- USO EXCLUSIVO EM DEV.

    Antes: so exigia @login_required, entao qualquer usuario autenticado
    podia ativar assinatura de graca (e nem filtrava por dono da
    transacao). Agora: exige is_staff E DEBUG=True, e continua nao
    exposto em producao de forma alguma.
    """
    if not (request.user.is_staff and settings.DEBUG):
        return JsonResponse({'error': 'Nao disponivel.'}, status=404)

    transacao = get_object_or_404(TransacaoMPESA, id=transacao_id, usuario=request.user)

    transacao.status = 'sucesso'
    transacao.save()

    ativar_assinatura(transacao.usuario, transacao.plano)

    return JsonResponse({'status': 'sucesso', 'mensagem': 'Pagamento simulado com sucesso'})


# ============================================
# CLIENTES
# ============================================
@login_required
@verificar_assinatura
def lista_clientes(request):
    clientes = Cliente.objects.filter(usuario=request.user)
    return render(request, 'clientes/lista.html', {'clientes': clientes})


@login_required
@verificar_assinatura
def cliente_cadastrar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        renda_mensal_raw = request.POST.get('renda_mensal', '').replace('.', '').replace(',', '.')
        data_nascimento = request.POST.get('data_nascimento', '')
        endereco = request.POST.get('endereco', '').strip()
        observacoes = request.POST.get('observacoes', '').strip()

        if not nome:
            messages.error(request, 'Nome e obrigatorio.')
            return render(request, 'clientes/formulario.html')

        if not telefone:
            messages.error(request, 'Telefone e obrigatorio.')
            return render(request, 'clientes/formulario.html')

        try:
            renda_mensal = float(renda_mensal_raw) if renda_mensal_raw else None
        except ValueError:
            messages.error(request, 'Renda mensal invalida.')
            return render(request, 'clientes/formulario.html')

        Cliente.objects.create(
            usuario=request.user,
            nome=nome,
            email=email if email else None,
            telefone=telefone,
            renda_mensal=renda_mensal,
            data_nascimento=data_nascimento if data_nascimento else None,
            endereco=endereco if endereco else None,
            observacoes=observacoes if observacoes else None,
        )

        messages.success(request, f'Cliente "{nome}" cadastrado com sucesso!')
        return redirect('clientes')

    return render(request, 'clientes/formulario.html')


@login_required
@verificar_assinatura
def cliente_editar(request, id):
    cliente = get_object_or_404(Cliente, id=id, usuario=request.user)

    if request.method == 'POST':
        cliente.nome = request.POST.get('nome', '').strip()
        cliente.email = request.POST.get('email', '').strip() or None
        cliente.telefone = request.POST.get('telefone', '').strip()
        renda_raw = request.POST.get('renda_mensal', '').replace('.', '').replace(',', '.')
        try:
            cliente.renda_mensal = float(renda_raw) if renda_raw else None
        except ValueError:
            messages.error(request, 'Renda mensal invalida.')
            return render(request, 'clientes/formulario.html', {'cliente': cliente})

        cliente.data_nascimento = request.POST.get('data_nascimento', '') or None
        cliente.endereco = request.POST.get('endereco', '').strip() or None
        cliente.observacoes = request.POST.get('observacoes', '').strip() or None
        cliente.save()

        messages.success(request, f'Cliente "{cliente.nome}" atualizado com sucesso!')
        return redirect('clientes')

    return render(request, 'clientes/formulario.html', {'cliente': cliente})


@login_required
@verificar_assinatura
def cliente_excluir(request, id):
    cliente = get_object_or_404(Cliente, id=id, usuario=request.user)
    nome = cliente.nome
    cliente.delete()
    messages.success(request, f'Cliente "{nome}" excluido com sucesso!')
    return redirect('clientes')


# ============================================
# EMPRESTIMOS
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
            messages.error(request, 'Todos os campos sao obrigatorios.')
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

        messages.success(request, f'Emprestimo de {cliente.nome} cadastrado com sucesso!')
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
    """
    API para baixar (marcar como pago) um emprestimo inteiro.

    Correcoes aplicadas:
    - Removido @csrf_exempt: antes tambem aceitava GET, o que tornava
      isto uma CSRF pronta para exploracao (uma tag <img src="..."> numa
      pagina maliciosa bastava para marcar o emprestimo como pago).
    - So aceita POST agora -- acao que altera estado nunca deve
      responder a GET.
    - Removida a checagem de permissao duplicada (existiam dois blocos
      identicos). Resposta de permissao negada agora e JSON (era um
      redirect, que nao faz sentido numa API consumida via fetch/AJAX).
    """
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if not funcionario.pode_baixar_emprestimos and funcionario.cargo != 'admin_empresa':
            return JsonResponse(
                {'success': False, 'error': 'Voce nao tem permissao para baixar emprestimos.'},
                status=403,
            )

    emprestimo = get_object_or_404(Emprestimo, id=id, usuario=request.user)

    if emprestimo.status == 'pago':
        return JsonResponse({'success': False, 'error': 'Emprestimo ja esta pago.'})

    emprestimo.status = 'pago'
    emprestimo.save()

    emprestimo.parcelas.update(status='pago', data_pagamento=timezone.now().date())

    return JsonResponse({'success': True, 'message': 'Emprestimo baixado com sucesso!'})


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
    """
    Registrar pagamento via AJAX.

    Correcoes: removido @csrf_exempt (o front deve mandar o token CSRF
    no header X-CSRFToken em vez de desativar a protecao); adicionado
    @login_required (antes acessava request.user sem garantir que
    estava autenticado); resposta de permissao negada trocada de
    redirect para JsonResponse, ja que e uma API.
    """
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if not funcionario.pode_regularizar_parcelas and funcionario.cargo != 'admin_empresa':
            return JsonResponse(
                {'success': False, 'error': 'Voce nao tem permissao para regularizar parcelas.'},
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
            return JsonResponse({'success': False, 'error': 'ID da parcela nao informado'})

        if not valor:
            return JsonResponse({'success': False, 'error': 'Valor nao informado'})

        if not forma_pagamento:
            return JsonResponse({'success': False, 'error': 'Forma de pagamento nao informada'})

        try:
            valor_float = float(valor)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Valor invalido'})

        parcela = Parcela.objects.get(id=parcela_id, emprestimo__usuario=request.user)

        if parcela.status == 'pago':
            return JsonResponse({'success': False, 'error': 'Esta parcela ja foi paga'})

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
        return JsonResponse({'success': False, 'error': 'Parcela nao encontrada'})

    except Exception as e:
        logger.error("Erro inesperado em registrar_pagamento: %s", e)
        return JsonResponse({'success': False, 'error': 'Erro interno ao registrar pagamento.'})


@login_required
@verificar_assinatura
def simular_juros(request, parcela_id):
    """Simular juros de uma parcela atrasada"""
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
        return JsonResponse({'error': 'Parcela nao encontrada'}, status=404)
    except Exception as e:
        logger.error("Erro em simular_juros: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


# ============================================
# RELATORIOS
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
    }

    return render(request, 'relatorio/geral.html', context)


@login_required
def pagar_parcela(request, parcela_id):
    """Pagina para pagar uma parcela"""
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
    """Pagina para regularizar uma parcela atrasada"""
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
# EMPRESA / CONFIGURACOES
# ============================================
@login_required
def empresa_config(request):
    """Configuracao da empresa"""
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
            messages.error(request, 'Verifique os valores numericos informados.')
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
            messages.error(request, 'Horario invalido. Use o formato HH:MM.')
            return render(request, 'empresa/config_notificacoes.html', {'config': config})

        config.save()

        messages.success(request, 'Configuracoes de notificacao salvas com sucesso!')
        return redirect('config_notificacoes')

    return render(request, 'empresa/config_notificacoes.html', {'config': config})


# ============================================
# NOTIFICACOES PUSH
# ============================================
@login_required
@csrf_exempt
@require_http_methods(['POST'])
def inscrever_push(request):
    """Endpoint para salvar inscricao push do usuario"""
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')

        if not subscription:
            return JsonResponse({'error': 'Subscription nao fornecida'}, status=400)

        PushSubscription.objects.filter(usuario=request.user).delete()

        obj = PushSubscription.objects.create(
            usuario=request.user,
            subscription_info=subscription,
            is_active=True,
        )

        logger.info("Nova inscricao push criada: id=%s user=%s", obj.id, request.user.pk)
        return JsonResponse({'success': True, 'created': True})

    except Exception as e:
        logger.error("Erro em inscrever_push: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


@login_required
def verificar_inscricao_push(request):
    """Verifica se o usuario ja tem uma inscricao push ativa"""
    has_subscription = PushSubscription.objects.filter(
        usuario=request.user,
        is_active=True
    ).exists()

    return JsonResponse({'has_subscription': has_subscription})


@login_required
@require_http_methods(['POST'])
def desinscrever_push(request):
    """Endpoint para remover inscricao push do usuario"""
    try:
        PushSubscription.objects.filter(usuario=request.user).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error("Erro em desinscrever_push: %s", e)
        return JsonResponse({'error': 'Erro interno.'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_fcm_device(request):
    """Registra um dispositivo FCM para o usuario"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario nao autenticado'}, status=401)

    try:
        data = json.loads(request.body)
        token = data.get('registration_id')

        if not token:
            return JsonResponse({'error': 'Token nao fornecido'}, status=400)

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
# GERENCIAMENTO DE FUNCIONARIOS
# ============================================
@login_required
def gerenciar_funcionarios(request):
    """Lista e gerencia funcionarios da empresa"""
    if not hasattr(request.user, 'empresa'):
        messages.error(request, 'Voce nao possui uma empresa associada.')
        return redirect('dashboard')

    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if funcionario.cargo != 'admin_empresa':
            messages.error(request, 'Apenas administradores podem gerenciar funcionarios.')
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
            messages.success(request, f'Funcionario {username} criado com sucesso!')
        return redirect('gerenciar_funcionarios')

    return render(request, 'funcionarios/gerenciar.html', {'funcionarios': funcionarios})


# ============================================
# PAGINAS LEGAIS
# ============================================
def termos_e_condicoes(request):
    """Pagina de Termos e Condicoes de Uso"""
    return render(request, 'legal/termos_e_condicoes.html')


def politica_privacidade(request):
    """Pagina de Politica de Privacidade"""
    return render(request, 'legal/politica_privacidade.html')