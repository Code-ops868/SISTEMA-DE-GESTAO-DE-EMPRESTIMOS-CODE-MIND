# ============================================
# MIDDLEWARE DE PERMISSÕES
# ============================================

import logging
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib import messages

logger = logging.getLogger('django.security')


class PermissaoMiddleware:
    """
    Middleware para verificar permissões de funcionários.

    Comportamento: default-deny para as URLs sensíveis listadas abaixo.
    Se o usuário autenticado não tiver perfil `funcionario`, o acesso a
    essas URLs é bloqueado (antes era liberado por omissão).
    """

    # URLs que requerem permissão especial
    URLS_BAIXAR = ['emprestimo_baixar', 'emprestimo_baixar_api', 'baixar_parcela']
    URLS_REGULARIZAR = ['registrar_pagamento']
    URLS_CONFIG = ['empresa_config', 'config_notificacoes']

    # URLs de API dentro das listas acima — recebem resposta JSON em vez
    # de redirect, para não quebrar chamadas fetch()/AJAX.
    URLS_API = ['emprestimo_baixar_api']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def _negar(self, request, url_name, mensagem, url_redirect):
        """Centraliza a resposta de negação: JSON para API, redirect para o resto."""
        funcionario_id = getattr(getattr(request.user, 'funcionario', None), 'id', None)
        logger.warning(
            "Permissao negada: user=%s funcionario_id=%s url=%s",
            request.user.pk, funcionario_id, url_name,
        )
        if url_name in self.URLS_API:
            return JsonResponse({'erro': mensagem}, status=403)
        messages.error(request, mensagem)
        return redirect(url_redirect)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Só verifica usuários autenticados
        if not request.user.is_authenticated:
            return None

        # Usa o resolver_match já calculado pelo Django em vez de
        # chamar resolve() de novo.
        url_name = (
            request.resolver_match.url_name
            if request.resolver_match else None
        )

        urls_sensiveis = self.URLS_BAIXAR + self.URLS_REGULARIZAR + self.URLS_CONFIG
        if url_name not in urls_sensiveis:
            return None

        # Superuser do Django sempre passa (equivalente ao admin_empresa)
        if request.user.is_superuser:
            return None

        # Não tem perfil de funcionário mas está tentando acessar uma URL
        # sensível: antes isso liberava por omissão, agora bloqueia.
        if not hasattr(request.user, 'funcionario'):
            return self._negar(
                request, url_name,
                '❌ Você não tem permissão para acessar este recurso.',
                'dashboard',
            )

        funcionario = request.user.funcionario

        # Se é admin da empresa, permite tudo
        if funcionario.cargo == 'admin_empresa':
            return None

        # Verificar permissão para baixar empréstimos
        if url_name in self.URLS_BAIXAR:
            if not funcionario.pode_baixar_emprestimos:
                return self._negar(
                    request, url_name,
                    '❌ Você não tem permissão para baixar empréstimos.',
                    'dashboard',
                )

        # Verificar permissão para regularizar parcelas
        if url_name in self.URLS_REGULARIZAR:
            if not funcionario.pode_regularizar_parcelas:
                return self._negar(
                    request, url_name,
                    '❌ Você não tem permissão para regularizar parcelas.',
                    'pagamentos',
                )

        # Verificar permissão para configurar empresa
        if url_name in self.URLS_CONFIG:
            if not funcionario.pode_configurar_empresa:
                return self._negar(
                    request, url_name,
                    '❌ Você não tem permissão para configurar a empresa.',
                    'dashboard',
                )

        return None