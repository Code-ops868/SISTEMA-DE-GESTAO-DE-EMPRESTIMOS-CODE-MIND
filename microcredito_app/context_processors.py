from .models import Notificacao

def notificacoes(request):
    print("🔍 CONTEXT PROCESSOR EXECUTANDO...")
    print(f"Usuário autenticado: {request.user.is_authenticated}")
    
    if request.user.is_authenticated:
        try:
            empresa = request.user.empresa
            print(f"Empresa: {empresa.nome}")
            
            notificacoes = Notificacao.objects.filter(
                empresa=empresa,
                status='pendente'
            ).order_by('-data_envio')[:10]
            
            total = notificacoes.count()
            print(f"Total encontrado: {total}")
            
            return {
                'notificacoes': notificacoes,
                'total_notificacoes': total,
            }
        except Exception as e:
            print(f"ERRO: {e}")
    
    return {
        'notificacoes': [],
        'total_notificacoes': 0,
    }