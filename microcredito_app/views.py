from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
# firebase
from django.views.decorators.csrf import csrf_exempt
from fcm_django.models import FCMDevice
import dns.resolver

#================================
import json
from .models import PushSubscription
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils import timezone

from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import (
    Parcela, Pagamento, Emprestimo, Cliente,
    Assinatura, Plano, PagamentoAssinatura, TransacaoMPESA)
from .models import Empresa
from .mpesa_service import MPESAService
from .forms import CadastroForm, LoginForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
# ============================================
# VIEWS PARA PUSH NOTIFICATIONS
# ============================================
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import PushSubscription

# ============================================
#importacoes de email
from django.core.mail import send_mail
from django.conf import settings
import secrets
from .models import EmailVerificacao
#=============================================
# PÁGINAS PÚBLICAS
# ============================================
def inicio(request):
    return render(request, 'inicio.html')

# login view
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            senha = form.cleaned_data['senha']
            lembrar = form.cleaned_data['lembrar']
            
            try:
                user = User.objects.get(email=email)
                user_authenticated = authenticate(request, username=user.username, password=senha)
                
                if user_authenticated:
                    login(request, user_authenticated)
                    if not lembrar:
                        request.session.set_expiry(0)
                    
                    # ✅ VERIFICAR ASSINATURA
                    try:
                        assinatura = Assinatura.objects.get(usuario=user_authenticated)
                        if assinatura.status != 'ativa':
                            messages.info(request, 'Escolha um plano para acessar o sistema.')
                            return redirect('planos')
                    except Assinatura.DoesNotExist:
                        # NÃO CRIAR ASSINATURA - apenas redirecionar para planos
                        messages.info(request, 'Escolha um plano para acessar o sistema.')
                        return redirect('planos')
                    
                    messages.success(request, f'Bem-vindo de volta, {user.first_name or user.username}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Senha incorreta.')
            except User.DoesNotExist:
                messages.error(request, 'E-mail não cadastrado.')
        else:
            for error in form.errors.values():
                messages.error(request, error)
        
        return render(request, 'auth/login.html', {'form': form})
    
    form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})

#======cadastro================
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
        
        # ============================================
        # VALIDAÇÃO DE EMAIL (NOVA)
        # ============================================
        if not email:
            messages.error(request, 'E-mail é obrigatório.')
            return render(request, 'auth/cadastro.html')
        
        # Validar formato do email
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            messages.error(request, 'Digite um e-mail válido (exemplo: nome@dominio.com)')
            return render(request, 'auth/cadastro.html')
        
        # Validar domínios temporários/bloqueados
        dominio = email.split('@')[1].lower()
        dominios_bloqueados = [
            'temp-mail.com', 'mailinator.com', 'guerrillamail.com',
            '10minutemail.com', 'throwawaymail.com', 'yopmail.com',
            'fakeinbox.com', 'mailnator.com', 'getairmail.com',
            'sharklasers.com', 'guerrillamail.net', 'guerrillamail.org',
            'mailmetrash.com', 'trashmail.com', 'tempemail.net',
            'tempmail.com', 'mohmal.com', 'dispostable.com'
        ]
        
        if dominio in dominios_bloqueados:
            messages.error(request, 'Não é permitido usar e-mails temporários ou descartáveis.')
            return render(request, 'auth/cadastro.html')
        
        # Validar se o domínio tem servidor de email (MX) - opcional
        try:
          
            dns.resolver.resolve(dominio, 'MX')
        except:
            # Se não conseguir validar DNS, apenas avisa mas permite (para testes locais)
            print(f"⚠️ Não foi possível validar o domínio: {dominio}")
        
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
        
        if len(senha1) < 6:
            messages.error(request, 'A senha deve ter no mínimo 6 caracteres.')
            return render(request, 'auth/cadastro.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail já está cadastrado.')
            return render(request, 'auth/cadastro.html')
        
        # Criar username automaticamente
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
                last_name=last_name
            )
            
            # ============================================
            # USUÁRIO FICA INATIVO ATÉ CONFIRMAR EMAIL
            # ============================================
            user.is_active = False
            user.save()
            
            # ============================================
            # GERAR CÓDIGO DE VERIFICAÇÃO
            # ============================================
            codigo = secrets.token_urlsafe(32)
            expiracao = timezone.now() + timedelta(hours=24)
            
            EmailVerificacao.objects.create(
                usuario=user,
                codigo=codigo,
                expira_em=expiracao
            )
            
            # ============================================
            # ENVIAR EMAIL DE CONFIRMAÇÃO
            # ============================================
            link = request.build_absolute_uri(f'/confirmar-email/{codigo}/')
            
            try:
                send_mail(
                    subject='Confirme seu cadastro - CODE-MIND',
                    message=f'''
Olá {first_name}!

Obrigado por se cadastrar na CODE-MIND.

Para ativar sua conta e começar a usar o sistema, clique no link abaixo:

{link}

Este link é válido por 24 horas.

Se você não solicitou este cadastro, ignore este email.

Atenciosamente,
Equipe CODE-MIND
                    ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, f'✅ Cadastro realizado, {first_name}! Enviamos um link de confirmação para seu email. Verifique sua caixa de entrada.')
            except Exception as e:
                print(f"Erro ao enviar email: {e}")
                messages.warning(request, 'Cadastro realizado, mas houve erro ao enviar email de confirmação. Entre em contato com o suporte.')
            
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar conta: {str(e)}')
            return render(request, 'auth/cadastro.html')
    
    return render(request, 'auth/cadastro.html')
# view para confirmar email
def confirmar_email_view(request, codigo):
    """Confirma o email do usuário e ativa a conta"""
    from django.utils import timezone
    
    try:
        verificacao = EmailVerificacao.objects.get(codigo=codigo)
        
        # Verificar se já foi verificado
        if verificacao.verificado_em:
            messages.warning(request, '⚠️ Este email já foi verificado. Faça login.')
            return redirect('login')
        
        # Verificar se expirou
        if timezone.now() > verificacao.expira_em:
            messages.error(request, '❌ Este link de confirmação expirou. Solicite um novo.')
            return redirect('login')
        
        # Ativar usuário
        user = verificacao.usuario
        user.is_active = True
        user.save()
        
        # Marcar como verificado
        verificacao.verificado_em = timezone.now()
        verificacao.save()
        
        messages.success(request, '✅ Email confirmado! Agora você pode fazer login.')
        return redirect('login')
        
    except EmailVerificacao.DoesNotExist:
        messages.error(request, '❌ Link de confirmação inválido.')
        return redirect('login')

#Logout views
def logout_view(request):
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('inicio')


# ============================================
# DECORATOR PARA VERIFICAR ASSINATURA
# ============================================

def verificar_assinatura(view_func):
    """Decorator para verificar se o usuário tem assinatura ativa (admin tem acesso total)"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # ✅ ADMIN TEM ACESSO TOTAL
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
# PÁGINAS PROTEGIDAS (requerem assinatura ativa)
# ============================================
@login_required
@verificar_assinatura
def dashboard(request):
    # ✅ ADMIN NÃO PRECISA DE ASSINATURA
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
        data = hoje - timedelta(days=30*i)
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
        plano = Plano.objects.get(nome=plano_nome)
    except Plano.DoesNotExist:
        messages.error(request, 'Plano não encontrado.')
        return redirect('planos')
    
    return redirect('pagamento_mpesa', plano_nome=plano_nome)

# ============================================
# PLANOS E ASSINATURAS - CORRIGIDO
# ============================================
@login_required
def pagamento_mpesa(request, plano_nome):
    try:
        plano = Plano.objects.get(nome=plano_nome)
    except Plano.DoesNotExist:
        messages.error(request, 'Plano não encontrado.')
        return redirect('planos')
    
    # Se for GET, mostrar o formulário
    if request.method == 'GET':
        return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})
    
    # Se for POST, processar o pagamento (sem telefone)
    if request.method == 'POST':
        # ❌ REMOVER a validação do telefone
        # telefone = request.POST.get('telefone')  # ← Já não precisa
        
        # Gerar referência sem caracteres especiais
        import re
        import uuid
        nome_limpo = re.sub(r'[^A-Za-z]', '', plano.nome.upper())
        referencia = f"PLANO{nome_limpo}{uuid.uuid4().hex[:12].upper()}"
        
        # Criar transação pendente (sem telefone)
        transacao = TransacaoMPESA.objects.create(
            usuario=request.user,
            plano=plano,
            valor=plano.valor,
            telefone='',  # ← Vazio, pois será inserido no checkout
            referencia=referencia,
            status='pendente',
            checkout_request_id=None,
            merchant_request_id=None
        )
        
        # Iniciar pagamento (sem enviar telefone)
        mpesa = MPESAService()
        response = mpesa.stk_push('', float(plano.valor), referencia)  # ← Telefone vazio
        
        if response.get('error'):
            transacao.status = 'falhou'
            transacao.resultado = str(response)
            transacao.save()
            messages.error(request, f'Erro ao iniciar pagamento: {response.get("error")}')
            return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})
        
        # Atualizar transação
        transacao.checkout_request_id = response.get('CheckoutRequestID')
        transacao.merchant_request_id = response.get('MerchantRequestID')
        transacao.status = 'processando'
        transacao.save()
        
        # ✅ REDIRECIONAR para o checkout_url do PaySuite
        checkout_url = response.get('checkout_url')
        if checkout_url:
            return redirect(checkout_url)  # Cliente insere telefone no PaySuite
        else:
            messages.info(request, 'Pagamento iniciado. Complete no ambiente seguro do PaySuite.')
            return redirect('pagamento_mpesa_status', transacao_id=transacao.id)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)
#===========================================
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
    
    # Consultar status
    if transacao.checkout_request_id:
        mpesa = MPESAService()  # Criar instância
        status_response = mpesa.verificar_status(transacao.checkout_request_id)
        
        # Verificar se o pagamento foi concluído
        if status_response.get('ResultCode') == '0':
            transacao.status = 'sucesso'
            transacao.resultado = json.dumps(status_response)
            transacao.save()
            ativar_assinatura(request.user, transacao.plano)
            messages.success(request, 'Pagamento confirmado! Sua assinatura foi ativada.')
            return redirect('dashboard')
        elif status_response.get('ResultCode') == '1037':
            messages.info(request, 'Pagamento ainda em processamento. Aguarde a confirmação.')
    
    return render(request, 'planos/status_mpesa.html', {'transacao': transacao})


@csrf_exempt
def mpesa_callback(request):
    """Webhook para receber callbacks do PaySuite"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Extrair dados do callback
            checkout_request_id = None
            result_code = None
            
            # Tenta extrair no formato do PaySuite ou M-PESA
            if 'Body' in data:
                # Formato M-PESA
                callback_data = data.get('Body', {}).get('stkCallback', {})
                result_code = callback_data.get('ResultCode')
                checkout_request_id = callback_data.get('CheckoutRequestID')
            else:
                # Formato PaySuite
                event = data.get('event')
                event_data = data.get('data', {})
                
                if event == 'payment.success':
                    result_code = '0'
                    checkout_request_id = event_data.get('id')
                elif event == 'payment.failed':
                    result_code = '1032'
                    checkout_request_id = event_data.get('id')
            
            if result_code == '0':
                # Pagamento bem sucedido
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
            print(f"Erro no webhook: {e}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})
    
    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Method not allowed'})
#Ativar assinatura
def ativar_assinatura(usuario, plano):
    """Ativar assinatura do usuário após pagamento confirmado"""
    # Cria ou atualiza a assinatura
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

# view confirmar pagamento
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
        
        messages.success(request, f'Pagamento confirmado! Assinatura ativada.')
    
    return redirect('admin:index')


# simular callbacks para testes
@login_required
def simular_callback(request, transacao_id):
    transacao = get_object_or_404(TransacaoMPESA, id=transacao_id)
    
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
        renda_mensal = request.POST.get('renda_mensal', '').replace('.', '').replace(',', '.')
        data_nascimento = request.POST.get('data_nascimento', '')
        endereco = request.POST.get('endereco', '').strip()
        observacoes = request.POST.get('observacoes', '').strip()
        
        if not nome:
            messages.error(request, 'Nome é obrigatório.')
            return render(request, 'clientes/formulario.html')
        
        if not telefone:
            messages.error(request, 'Telefone é obrigatório.')
            return render(request, 'clientes/formulario.html')
        
        cliente = Cliente.objects.create(
            usuario=request.user,
            nome=nome,
            email=email if email else None,
            telefone=telefone,
            renda_mensal=float(renda_mensal) if renda_mensal else None,
            data_nascimento=data_nascimento if data_nascimento else None,
            endereco=endereco if endereco else None,
            observacoes=observacoes if observacoes else None
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
        renda = request.POST.get('renda_mensal', '').replace('.', '').replace(',', '.')
        cliente.renda_mensal = float(renda) if renda else None
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
    messages.success(request, f'Cliente "{nome}" excluído com sucesso!')
    return redirect('clientes')


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
        
        valor_limpo = valor.replace('.', '').replace(',', '.')
        cliente = get_object_or_404(Cliente, id=cliente_id, usuario=request.user)
        data_vencimento = datetime.strptime(data_primeiro_vencimento, '%Y-%m-%d').date()
        
        emprestimo = Emprestimo.objects.create(
            usuario=request.user,
            cliente=cliente,
            valor=float(valor_limpo),
            taxa_juros=float(taxa_juros),
            quantidade_parcelas=int(quantidade_parcelas),
            data_primeiro_vencimento=data_vencimento,
            tipo_juros=tipo_juros,
            status='ativo'
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
            status='pendente'
        )
        data_vencimento += timedelta(days=30)


@login_required
@verificar_assinatura
def emprestimo_parcelas(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id, usuario=request.user)
    parcelas = emprestimo.parcelas.all()
    return render(request, 'emprestimo/parcelas.html', {'emprestimo': emprestimo, 'parcelas': parcelas})

# para baixar o emprestimo inteiro(marcar como pago)
@login_required
@csrf_exempt

def emprestimo_baixar_api(request, id):
    """
    API para baixar empréstimo via AJAX (aceita GET e POST)
    """
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if not funcionario.pode_baixar_emprestimos and funcionario.cargo != 'admin_empresa':
            messages.error(request, '❌ Você não tem permissão para baixar empréstimos.')
            return redirect('emprestimo')
        
    # Aceitar tanto GET quanto POST
    if request.method not in ['GET', 'POST']:
        return JsonResponse({'success': False, 'error': 'Método não permitido.'})
    
    # ============================================
    # VERIFICAÇÃO DE PERMISSÃO (NOVO)
    # ============================================
    # Verificar permissão de funcionário
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        # Se não for admin_empresa e não tiver permissão para baixar
        if not funcionario.pode_baixar_emprestimos and funcionario.cargo != 'admin_empresa':
            return JsonResponse({'success': False, 'error': 'Você não tem permissão para baixar empréstimos.'})
    
    emprestimo = get_object_or_404(Emprestimo, id=id, usuario=request.user)
    
    if emprestimo.status == 'pago':
        return JsonResponse({'success': False, 'error': 'Empréstimo já está pago.'})
    
    emprestimo.status = 'pago'
    emprestimo.save()
    
    # Marcar todas as parcelas como pagas
    emprestimo.parcelas.update(status='pago', data_pagamento=timezone.now().date())
    
    return JsonResponse({'success': True, 'message': 'Empréstimo baixado com sucesso!'})

# ============================================
# PAGAMENTOS - FUNÇÃO CORRIGIDA
# ============================================
# ============================================
# PAGAMENTOS - VERSÃO CORRIGIDA
# ============================================
@login_required
@verificar_assinatura
def pagamento(request):
    usuario = request.user
    hoje = date.today()
    
    # ============================================
    # PARCELAS PENDENTES (PRÓXIMAS)
    # ============================================
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
            'valor': float(p.valor),  # ✅ Já vem como número
            'valor_str': str(float(p.valor)).replace('.', ','),  # ✅ Envia como string com vírgula para o template
            'data_vencimento': p.data_vencimento,
            'dias_restantes': dias_restantes
        })
    
    # ============================================
    # PARCELAS ATRASADAS
    # ============================================
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
            'valor_total_str': str(float(valor_total)).replace('.', ','),  # ✅ Envia como string com vírgula
            'data_vencimento': p.data_vencimento,
            'dias_atraso': dias_atraso
        })
    
    # ============================================
    # HISTÓRICO DE PAGAMENTOS
    # ============================================
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
            'comprovante': pag.comprovante.url if pag.comprovante else None
        })
    
    # ============================================
    # CARDS DE RESUMO
    # ============================================
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
#==============verificar assinatura=================
@csrf_exempt
@require_http_methods(["POST"])
def registrar_pagamento(request):
    """Registrar pagamento via AJAX"""
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if not funcionario.pode_regularizar_parcelas and funcionario.cargo != 'admin_empresa':
            messages.error(request, '❌ Você não tem permissão para regularizar parcelas.')
            return redirect('pagamentos')
    
    if request.method == 'POST':
        try:
            print("=" * 50)
            print("📝 REGISTRAR PAGAMENTO CHAMADO")
            
            # Pegar os dados do POST
            parcela_id = request.POST.get('parcela_id')
            valor = request.POST.get('valor')
            forma_pagamento = request.POST.get('forma_pagamento')
            comprovante = request.FILES.get('comprovante')
            
            print(f"Parcela ID: {parcela_id}")
            print(f"Valor: {valor}")
            print(f"Forma Pagamento: {forma_pagamento}")
            
            # Validar dados
            if not parcela_id:
                return JsonResponse({'success': False, 'error': 'ID da parcela não informado'})
            
            if not valor:
                return JsonResponse({'success': False, 'error': 'Valor não informado'})
            
            if not forma_pagamento:
                return JsonResponse({'success': False, 'error': 'Forma de pagamento não informada'})
            
            # Buscar a parcela
            parcela = Parcela.objects.get(id=parcela_id, emprestimo__usuario=request.user)
            
            # Verificar se já está paga
            if parcela.status == 'pago':
                return JsonResponse({'success': False, 'error': 'Esta parcela já foi paga'})
            
            # Criar o pagamento (REMOVER 'usuario' se não existir no modelo)
            pagamento = Pagamento.objects.create(
                parcela=parcela,
                valor=float(valor),
                forma_pagamento=forma_pagamento,
                comprovante=comprovante
                # REMOVIDO: usuario=request.user
            )
            
            # Atualizar status da parcela
            parcela.status = 'pago'
            parcela.data_pagamento = timezone.now().date()
            parcela.save()
            
            print(f"✅ Pagamento criado com sucesso! ID: {pagamento.id}")
            
            return JsonResponse({
                'success': True,
                'message': f'Pagamento de MT {float(valor):.2f} registrado com sucesso!',
                'pagamento_id': pagamento.id
            })
            
        except Parcela.DoesNotExist:
            print("❌ Parcela não encontrada")
            return JsonResponse({'success': False, 'error': 'Parcela não encontrada'})
        
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Erro: {str(e)}'})
# Simular juros
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
                'valor_total': float(parcela.valor)
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
            'valor_total': valor_total
        })
    except Parcela.DoesNotExist:
        return JsonResponse({'error': 'Parcela não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# ============================================
# RELATÓRIOS
# ============================================
cadastro_view
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
            'percentual': round(percentual, 1)
        })
    
    monthly_labels = []
    monthly_data = []
    for i in range(5, -1, -1):
        data = hoje - timedelta(days=30*i)
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
    """Página para pagar uma parcela"""
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
            observacoes=observacoes
        )
        
        messages.success(request, f'✅ Pagamento da parcela {parcela.numero} registrado com sucesso!')
        return redirect('pagamentos')
    
    return render(request, 'pagamentos/pagar.html', {'parcela': parcela})

#regularizar parcela
@login_required
def regularizar_parcela(request, parcela_id):
    """Página para regularizar uma parcela atrasada"""
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
                'valor_total': valor_total
            })
        
        Pagamento.objects.create(
            parcela=parcela,
            valor=valor_total,
            forma_pagamento=forma_pagamento,
            comprovante=comprovante,
            observacoes=observacoes
        )
        
        messages.success(request, f'✅ Pagamento da parcela {parcela.numero} regularizado com sucesso!')
        return redirect('pagamentos')
    
    return render(request, 'pagamentos/regularizar.html', {
        'parcela': parcela,
        'dias_atraso': dias_atraso,
        'multa': multa,
        'juros': juros,
        'valor_total': valor_total
    })

#===================Empresa config================================

@login_required
def empresa_config(request):
    """Configuração da empresa"""
    empresa, created = Empresa.objects.get_or_create(
        user=request.user,
        defaults={
            'nome': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'status': 'ativa'
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

#------------------config notificacoes-------------------------------------
from .models import ConfiguracaoNotificacao

# views.py
@login_required
def config_notificacoes(request):
    try:
        empresa = Empresa.objects.get(user=request.user)
        config, created = ConfiguracaoNotificacao.objects.get_or_create(empresa=empresa)
    except Empresa.DoesNotExist:
        messages.error(request, 'Configure primeiro os dados da sua empresa.')
        return redirect('empresa_config')
    
    if request.method == 'POST':
        # Configurações existentes (WhatsApp/SMS/Email)
        config.whatsapp_token = request.POST.get('whatsapp_token')
        config.whatsapp_phone_id = request.POST.get('whatsapp_phone_id')
        config.sms_api_key = request.POST.get('sms_api_key')
        config.notificar_vencimento = request.POST.get('notificar_vencimento') == 'on'
        config.notificar_atraso = request.POST.get('notificar_atraso') == 'on'
        config.dias_antecedencia = int(request.POST.get('dias_antecedencia', 5))
        config.atraso_frequencia = int(request.POST.get('atraso_frequencia', 2))
        
        # ✅ Novas configurações Push
        config.push_notificacoes_ativas = request.POST.get('push_notificacoes_ativas') == 'on'
        config.push_alertar_vencimento = request.POST.get('push_alertar_vencimento') == 'on'
        config.push_alertar_atraso = request.POST.get('push_alertar_atraso') == 'on'
        config.push_dias_antecedencia = int(request.POST.get('push_dias_antecedencia', 3))
        
        # Horários
        from datetime import datetime
        horario_inicio = request.POST.get('push_horario_inicio')
        horario_fim = request.POST.get('push_horario_fim')
        if horario_inicio:
            config.push_horario_inicio = datetime.strptime(horario_inicio, '%H:%M').time()
        if horario_fim:
            config.push_horario_fim = datetime.strptime(horario_fim, '%H:%M').time()
        
        config.save()
        
        messages.success(request, 'Configurações de notificação salvas com sucesso!')
        return redirect('config_notificacoes')
    
    return render(request, 'empresa/config_notificacoes.html', {'config': config})
# notificacoes push


@login_required
@csrf_exempt
@require_http_methods(['POST'])
def inscrever_push(request):
    """
    Endpoint para salvar inscrição push do usuário
    """
    print("🔍 View inscrever_push foi chamada")
    
    try:
        data = json.loads(request.body)
        print(f"📦 Dados recebidos: {data}")
        
        subscription = data.get('subscription')
        
        if not subscription:
            return JsonResponse({'error': 'Subscription não fornecida'}, status=400)
        
        # REMOVER inscrições antigas do mesmo usuário
        PushSubscription.objects.filter(usuario=request.user).delete()
        
        # CRIAR nova inscrição
        obj = PushSubscription.objects.create(
            usuario=request.user,
            subscription_info=subscription,
            is_active=True
        )
        
        print(f"✅ Nova inscrição criada (ID: {obj.id})")
        return JsonResponse({'success': True, 'created': True})
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    
# Endpoint para verificar inscricao push
emprestimo_baixar_api
@login_required
def verificar_inscricao_push(request):
    """
    Verifica se o usuário já tem uma inscrição push ativa
    """
    print("🔍 View verificar_inscricao_push foi chamada")  # Para debug
    
    has_subscription = PushSubscription.objects.filter(
        usuario=request.user, 
        is_active=True
    ).exists()
    
    print(f"📊 Usuário tem inscrição ativa: {has_subscription}")  # Para debug
    
    return JsonResponse({'has_subscription': has_subscription})

@login_required
@require_http_methods(['POST'])
def desinscrever_push(request):
    """
    Endpoint para remover inscrição push do usuário
    """
    print("🔍 View desinscrever_push foi chamada")  # Para debug
    
    try:
        PushSubscription.objects.filter(usuario=request.user).delete()
        print("✅ Inscrição removida com sucesso")  # Para debug
        return JsonResponse({'success': True})
    except Exception as e:
        print(f"❌ Erro ao remover: {e}")  # Para debug
        return JsonResponse({'error': str(e)}, status=500)

# firebase

pagamento_mpesa
@csrf_exempt
@require_http_methods(["POST"])
def register_fcm_device(request):
    """Registra um dispositivo FCM para o usuário"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuário não autenticado'}, status=401)
    
    try:
        data = json.loads(request.body)
        token = data.get('registration_id')
        
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=400)
        
        # Buscar ou criar dispositivo
        device, created = FCMDevice.objects.get_or_create(
            registration_id=token,
            defaults={
                'user': request.user,
                'type': 'web',
                'active': True
            }
        )
        
        if not created:
            # Atualizar dispositivo existente
            device.user = request.user
            device.active = True
            device.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Dispositivo registrado com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# gerenciamento de funcionarios
from .models import Funcionario
from django.contrib.auth.models import User

@login_required
def gerenciar_funcionarios(request):
    """Lista e gerencia funcionários da empresa"""
    if not hasattr(request.user, 'empresa'):
        messages.error(request, 'Você não possui uma empresa associada.')
        return redirect('dashboard')
    
    # Verificar se é admin da empresa
    if hasattr(request.user, 'funcionario'):
        funcionario = request.user.funcionario
        if funcionario.cargo != 'admin_empresa':
            messages.error(request, '❌ Apenas administradores podem gerenciar funcionários.')
            return redirect('dashboard')
    
    funcionarios = Funcionario.objects.filter(empresa=request.user.empresa)
    
    if request.method == 'POST':
        # Criar novo funcionário
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cargo = request.POST.get('cargo')
        
        if username and email and password:
            user = User.objects.create_user(username=username, email=email, password=password)
            Funcionario.objects.create(
                usuario=user,
                empresa=request.user.empresa,
                cargo=cargo,
                pode_baixar_emprestimos=request.POST.get('pode_baixar') == 'on',
                pode_regularizar_parcelas=request.POST.get('pode_regularizar') == 'on',
                pode_configurar_empresa=request.POST.get('pode_configurar') == 'on',
                ativo=True
            )
            messages.success(request, f'✅ Funcionário {username} criado com sucesso!')
        return redirect('gerenciar_funcionarios')
    
    return render(request, 'funcionarios/gerenciar.html', {'funcionarios': funcionarios})

# Termos e condicoes
def termos_e_condicoes(request):
    """Página de Termos e Condições de Uso"""
    return render(request, 'legal/termos_e_condicoes.html')

# Politicas de privacidade
def politica_privacidade(request):
    """Página de Política de Privacidade"""
    return render(request, 'legal/politica_privacidade.html')
