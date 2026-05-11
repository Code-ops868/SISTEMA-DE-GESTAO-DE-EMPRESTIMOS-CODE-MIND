# ============================================
# MIDDLEWARE DE PERMISSÕES
# ============================================

from django.shortcuts import redirect
from django.urls import resolve
from django.contrib import messages

class PermissaoMiddleware:
    """
    Middleware para verificar permissões de funcionários
    """
    
    # URLs que requerem permissão especial
    URLS_BAIXAR = ['emprestimo_baixar', 'emprestimo_baixar_api', 'baixar_parcela']
    URLS_REGULARIZAR = ['registrar_pagamento']
    URLS_CONFIG = ['empresa_config', 'config_notificacoes']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Só verifica usuários autenticados
        if not request.user.is_authenticated:
            return None
        
        # Verificar se é funcionário (tem o profile)
        if hasattr(request.user, 'funcionario'):
            funcionario = request.user.funcionario
            
            # Se é admin da empresa, permite tudo
            if funcionario.cargo == 'admin_empresa':
                return None
            
            # Obter o nome da URL atual
            url_name = resolve(request.path_info).url_name
            
            # Verificar permissão para baixar empréstimos
            if url_name in self.URLS_BAIXAR:
                if not funcionario.pode_baixar_emprestimos:
                    messages.error(request, '❌ Você não tem permissão para baixar empréstimos.')
                    return redirect('dashboard')
            
            # Verificar permissão para regularizar parcelas
            if url_name in self.URLS_REGULARIZAR:
                if not funcionario.pode_regularizar_parcelas:
                    messages.error(request, '❌ Você não tem permissão para regularizar parcelas.')
                    return redirect('pagamentos')
            
            # Verificar permissão para configurar empresa
            if url_name in self.URLS_CONFIG:
                if not funcionario.pode_configurar_empresa:
                    messages.error(request, '❌ Você não tem permissão para configurar a empresa.')
                    return redirect('dashboard')
        
        return None