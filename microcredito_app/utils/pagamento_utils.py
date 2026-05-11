# microcredito_app/utils/pagamento_utils.py
from decimal import Decimal
import uuid
import logging
from django.utils import timezone
from microcredito_app.models import TransacaoMPESA, Plano, Assinatura
from microcredito_app import mpesa_service

logger = logging.getLogger(__name__)
def criar_pagamento_paysuite(usuario, plano_id, telefone, metodo='emola'):
    """
    Criar transação e iniciar pagamento com PaySuite
    
    Args:
        usuario: Usuário autenticado
        plano_id: ID do plano
        telefone: Número de telefone
        metodo: 'emola' ou 'mpesa'
    
    Returns:
        dict: Resultado da operação
    """
    try:
        plano = Plano.objects.get(id=plano_id)
        
        # Gerar referência única
        referencia = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        
        # Criar transação no modelo existente
        transacao = TransacaoMPESA.objects.create(
            usuario=usuario,
            plano=plano,
            valor=plano.valor,
            telefone=telefone,
            referencia=referencia,
            status='pendente'
        )
        
        # Iniciar pagamento no PaySuite
        resultado = mpesa_service.iniciar_pagamento(transacao, metodo=metodo)
        
        if resultado['success']:
            return {
                'success': True,
                'transacao': transacao,
                'payment_id': resultado['payment_id'],
                'checkout_url': resultado['checkout_url']
            }
        else:
            return {
                'success': False,
                'error': resultado.get('error', 'Erro ao processar pagamento'),
                'transacao': transacao
            }
            
    except Plano.DoesNotExist:
        return {
            'success': False,
            'error': 'Plano não encontrado'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def processar_pagamento_sucesso(transacao):
    """
    Processar pagamento bem sucedido - ativar assinatura
    """
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Buscar ou criar assinatura do usuário
        assinatura, created = Assinatura.objects.get_or_create(
            usuario=transacao.usuario,
            defaults={
                'plano': transacao.plano,
                'status': 'ativa',
                'data_inicio': timezone.now(),
                'data_expiracao': timezone.now() + timedelta(days=transacao.plano.duracao_dias),
                'data_pagamento': timezone.now()
            }
        )
        
        if not created:
            # Atualizar assinatura existente
            assinatura.plano = transacao.plano
            assinatura.status = 'ativa'
            assinatura.data_inicio = timezone.now()
            assinatura.data_expiracao = timezone.now() + timedelta(days=transacao.plano.duracao_dias)
            assinatura.data_pagamento = timezone.now()
            assinatura.save()
        
        # Criar registro de pagamento
        from microcredito_app.models import PagamentoAssinatura
        PagamentoAssinatura.objects.create(
            usuario=transacao.usuario,
            plano=transacao.plano,
            valor=transacao.valor,
            forma_pagamento='emola' if 'emola' in str(transacao.resultado).lower() else 'pix',
            status='pago',
            comprovante=None
        )
        
        return {
            'success': True,
            'assinatura': assinatura
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar pagamento sucesso: {e}")
        return {
            'success': False,
            'error': str(e)
        }