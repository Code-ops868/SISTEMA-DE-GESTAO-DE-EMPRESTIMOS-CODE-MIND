from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Plano, TransacaoMPESA
from mpesa_service import MPESAService
import uuid

@login_required
def pagamento_mpesa(request, plano_nome):
    """
    MODO REAL - Chama a API M-PESA
    Requer credenciais válidas e produto M-PESA ativado
    """
    try:
        plano = Plano.objects.get(nome=plano_nome)
    except Plano.DoesNotExist:
        messages.error(request, 'Plano não encontrado.')
        return redirect('planos')
    
    if request.method == 'POST':
        telefone = request.POST.get('telefone')
        
        if not telefone:
            messages.error(request, 'Número de telefone é obrigatório.')
            return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})
        
        referencia = f"PLANO-{plano.nome.upper()}-{uuid.uuid4().hex[:8].upper()}"
        
        # Criar transação pendente
        transacao = TransacaoMPESA.objects.create(
            usuario=request.user,
            plano=plano,
            valor=plano.valor,
            telefone=telefone,
            referencia=referencia,
            status='pendente'
        )
        
        # Chamar API real
        mpesa = MPESAService()
        response = mpesa.stk_push(telefone, float(plano.valor), referencia)
        
        if response.get('error'):
            transacao.status = 'falhou'
            transacao.resultado = str(response)
            transacao.save()
            messages.error(request, f'Erro ao iniciar pagamento: {response.get("error")}')
            return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})
        
        transacao.checkout_request_id = response.get('CheckoutRequestID')
        transacao.merchant_request_id = response.get('MerchantRequestID')
        transacao.status = 'processando'
        transacao.save()
        
        messages.info(request, f'Pagamento iniciado. Confirme no seu telefone {telefone}')
        return redirect('pagamento_mpesa_status', transacao_id=transacao.id)
    
    return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})