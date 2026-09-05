from . import views
from django.urls import path
from .views import inscrever_push, desinscrever_push, verificar_inscricao_push
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ============================================
    # LOGIN / AUTENTICAÇÃO
    # ============================================
    path('', views.inicio, name='inicio'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ============================================
    # CLIENTES - COM DOCUMENTOS MOÇAMBICANOS
    # ============================================
    path('clientes/', views.lista_clientes, name='clientes'),
    path('clientes/novo/', views.cliente_cadastrar, name='cliente_cadastrar'),
    path('clientes/editar/<int:id>/', views.cliente_editar, name='cliente_editar'),
    path('clientes/excluir/<int:id>/', views.cliente_excluir, name='cliente_excluir'),
    
    # ============================================
    # API - VALIDAÇÃO DE DOCUMENTOS EM TEMPO REAL
    # ============================================
    path('api/validar-documento/', views.validar_documento_api, name='validar_documento_api'),
    
    # ============================================
    # EMPRÉSTIMOS
    # ============================================
    path('emprestimo/', views.lista_emprestimos, name='emprestimo'),
    path('emprestimo/novo/', views.emprestimo_cadastrar, name='emprestimo_cadastrar'),
    path('emprestimo/parcelas/<int:id>/', views.emprestimo_parcelas, name='emprestimo_parcelas'),
    path('emprestimos/baixar/<int:id>/', views.emprestimo_baixar_api, name='emprestimo_baixar_api'),
    
    # ============================================
    # PAGAMENTOS
    # ============================================
    path('pagamento/', views.pagamento, name='pagamento'),
    path('registrar-pagamento/', views.registrar_pagamento, name='registrar_pagamento'),
    path('simular-juros/<int:parcela_id>/', views.simular_juros, name='simular_juros'),
    
    # ============================================
    # PLANOS E ASSINATURAS
    # ============================================
    path('planos/', views.planos, name='planos'),
    path('pagamento-plano/<str:plano_nome>/', views.pagamento_plano, name='pagamento_plano'),
    path('confirmar-pagamento/<int:pagamento_id>/', views.confirmar_pagamento, name='confirmar_pagamento'),
    
    # ============================================
    # M-PESA
    # ============================================
    path('mpesa/pagamento/<str:plano_nome>/', views.pagamento_mpesa, name='pagamento_mpesa'),
    path('mpesa/status/<int:transacao_id>/', views.pagamento_mpesa_status, name='pagamento_mpesa_status'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # ============================================
    # RELATÓRIOS
    # ============================================
    path('relatorios/', views.relatorios, name='relatorios'),
    path('pagamentos/', views.pagamento, name='pagamentos'),
    path('pagamento/pagar/<int:parcela_id>/', views.pagar_parcela, name='pagar_parcela'),
    path('pagamento/regularizar/<int:parcela_id>/', views.regularizar_parcela, name='regularizar_parcela'),
    
    # ============================================
    # EMPRESA / CONFIGURAÇÕES
    # ============================================
    path('empresa/config/', views.empresa_config, name='empresa_config'),
    path('empresa/config-notificacoes/', views.config_notificacoes, name='config_notificacoes'),
    
    # ============================================
    # NOTIFICAÇÕES PUSH
    # ============================================
    path('notificacoes/inscrever_push/', inscrever_push, name='inscrever_push'),
    path('notificacoes/desinscrever_push/', desinscrever_push, name='desinscrever_push'),
    path('notificacoes/verificar_inscricao/', verificar_inscricao_push, name='verificar_inscricao_push'),
    
    # ============================================
    # FIREBASE FCM
    # ============================================
    path('api/devices/', views.register_fcm_device, name='register_fcm_device'),
    path('firebase-messaging-sw.js', 
         TemplateView.as_view(
             template_name='firebase-messaging-sw.js',
             content_type='application/javascript'
         ),
         name='firebase-messaging-sw.js'),
    
    # ============================================
    # FUNCIONÁRIOS
    # ============================================
    path('empresa/funcionarios/', views.gerenciar_funcionarios, name='gerenciar_funcionarios'),
    
    # ============================================
    # PAINEL ADMINISTRATIVO - EMPRESAS E FACTURAÇÃO
    # ============================================
    path('admin-painel/empresas/', views.admin_lista_empresas, name='admin_lista_empresas'),
    path('admin-painel/empresas/<int:empresa_id>/relatorio/', views.admin_relatorio_empresa_pdf, name='admin_relatorio_empresa_pdf'),
    
    # ============================================
    # PÁGINAS LEGAIS
    # ============================================
    path('legal/termos_e_condicoes/', views.termos_e_condicoes, name='termos_e_condicoes'),
    path('legal/politica_privacidade/', views.politica_privacidade, name='politica_privacidade'),
    
    # ============================================
    # RECUPERAÇÃO DE SENHA
    # ============================================
    path('esqueci-senha/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('esqueci-senha/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('redefinir-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('redefinir-senha/concluido/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # ============================================
    # CONFIRMAÇÃO DE EMAIL
    # ============================================
    path('confirmar-email/<str:codigo>/', views.confirmar_email_view, name='confirmar_email'),
]