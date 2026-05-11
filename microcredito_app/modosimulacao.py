from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Plano, TransacaoMPESA
import uuid

@login_required
def pagamento_mpesa(request, plano_nome):
    """
    MODO SIMULAÇÃO - Pagamento aprovado automaticamente
    Não chama a API real do M-PESA
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
        
        # Simulação: transação criada como sucesso direto
        TransacaoMPESA.objects.create(
            usuario=request.user,
            plano=plano,
            valor=plano.valor,
            telefone=telefone,
            referencia=referencia,
            status='sucesso',
            checkout_request_id=f"SIM_{referencia}",
            merchant_request_id=f"SIM_{referencia}"
        )
        
        from .views import ativar_assinatura
        ativar_assinatura(request.user, plano)
        
        messages.success(request, f'✅ [SIMULAÇÃO] Pagamento realizado com sucesso! Assinatura ativada.')
        return redirect('dashboard')
    
    return render(request, 'planos/pagamento_mpesa.html', {'plano': plano})