from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


#-------------------classe para provincias e cidades de mocambique---------------------------------------------------------
# ============================================
# DADOS GEOGRÁFICOS DE MOÇAMBIQUE
# ============================================

class Provincia(models.Model):
    nome = models.CharField('Província', max_length=100, unique=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Província'
        verbose_name_plural = 'Províncias'
        ordering = ['nome']


class Cidade(models.Model):
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='cidades')
    nome = models.CharField('Cidade', max_length=100)
    
    def __str__(self):
        return f"{self.nome} - {self.provincia.nome}"
    
    class Meta:
        verbose_name = 'Cidade'
        verbose_name_plural = 'Cidades'
        ordering = ['nome']


class Distrito(models.Model):
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='distritos')
    nome = models.CharField('Distrito', max_length=100)
    
    def __str__(self):
        return f"{self.nome} - {self.provincia.nome}"
    
    class Meta:
        verbose_name = 'Distrito'
        verbose_name_plural = 'Distritos'
        ordering = ['nome']
# ============================================
# PLANOS DE ASSINATURA
# ============================================
class Plano(models.Model):
    TIPO_CHOICES = [
        ('mensal', 'Mensal'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
    ]
    
    nome = models.CharField('Nome do Plano', max_length=20, choices=TIPO_CHOICES)
    descricao = models.CharField('Descrição', max_length=100, blank=True)
    valor = models.DecimalField('Valor (MT)', max_digits=10, decimal_places=2)
    duracao_dias = models.IntegerField('Duração em Dias')
    periodo_teste = models.BooleanField('Período de Teste', default=False)
    
    def __str__(self):
        return f"{self.get_nome_display()} - {self.valor} MT"
    
    class Meta:
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'

#===============Mpesa=========================
# Adicionar ao models.py existente

class TransacaoMPESA(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('sucesso', 'Sucesso'),
        ('falhou', 'Falhou'),
        ('cancelado', 'Cancelado'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transacoes_mpesa')
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True)
    valor = models.DecimalField('Valor (MT)', max_digits=10, decimal_places=2)
    telefone = models.CharField('Telefone M-PESA', max_length=15)
    referencia = models.CharField('Referência', max_length=50, unique=True)
    checkout_request_id = models.CharField('Checkout Request ID', max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField('Merchant Request ID', max_length=100, blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    resultado = models.TextField('Resultado', blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.valor} MT - {self.status}"
    
    class Meta:
        verbose_name = 'Transação M-PESA'
        verbose_name_plural = 'Transações M-PESA'
        ordering = ['-data_criacao']
# ============================================
# ASSINATURA DO USUÁRIO
# ============================================
class Assinatura(models.Model):
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('expirada', 'Expirada'),
        ('cancelada', 'Cancelada'),
        ('teste', 'Período de Teste'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='assinatura')
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='teste')
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_expiracao = models.DateTimeField()
    data_pagamento = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_status_display()}"
    
    def is_active(self):
        from django.utils import timezone
        return self.status == 'ativa' and self.data_expiracao > timezone.now()
    
    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'


# ============================================
# PAGAMENTO DE ASSINATURA
# ============================================
class PagamentoAssinatura(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('falhou', 'Falhou'),
        ('cancelado', 'Cancelado'),
    ]
    
    FORMA_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('emola', 'E-MOLA'),
        ('mpesa', 'M-PESA'),
        ('transferencia', 'Transferência'),
        ('cartao', 'Cartão'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pagamentos_assinatura')
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True)
    valor = models.DecimalField('Valor (MT)', max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField('Forma de Pagamento', max_length=20, choices=FORMA_CHOICES)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    comprovante = models.FileField('Comprovante', upload_to='comprovantes_assinatura/', blank=True, null=True)
    data_pagamento = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.plano} - {self.valor} MT"
    
    class Meta:
        verbose_name = 'Pagamento de Assinatura'
        verbose_name_plural = 'Pagamentos de Assinatura'
        ordering = ['-data_pagamento']

# ============================================
# 1. PERFIL DO USUÁRIO (estende User)
# ============================================
class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField('Foto/Logo', upload_to='perfis/%Y/%m/', blank=True, null=True)
    telefone = models.CharField('Telefone/WhatsApp', max_length=15, blank=True, null=True)
    endereco = models.TextField('Endereço', blank=True, null=True)
    
    # Campos de localização
    provincia = models.ForeignKey(Provincia, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Província')
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Cidade')
    distrito = models.ForeignKey(Distrito, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Distrito')
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name() or self.user.username}"
    
    def get_localizacao(self):
        if self.cidade:
            return f"{self.cidade.nome}"
        elif self.distrito:
            return f"{self.distrito.nome} - {self.distrito.provincia.nome}"
        return "Não informado"
    
    class Meta:
        verbose_name = 'Perfil do Usuário'
        verbose_name_plural = 'Perfis dos Usuários'
# ============================================
# 2. CLIENTE (quem pega empréstimo)
# ============================================
class Cliente(models.Model):
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='clientes',
        verbose_name='Usuário Responsável'
    )
    nome = models.CharField('Nome Completo', max_length=200)
    email = models.EmailField('E-mail', blank=True, null=True)
    telefone = models.CharField(
        'Telefone/WhatsApp',
        max_length=15,
        help_text='Exemplo: 841234567 ou 851234567'
    )
    endereco = models.TextField('Endereço', blank=True, null=True)
    renda_mensal = models.DecimalField(
        'Renda Mensal (MT)',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Usado para análise de crédito'
    )
    data_nascimento = models.DateField('Data de Nascimento', blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-data_cadastro']
        unique_together = ['usuario', 'telefone']


# ============================================
# 3. EMPRÉSTIMO
# ============================================
class Emprestimo(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('pago', 'Pago'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]
    
    TIPO_JUROS_CHOICES = [
        ('simples', 'Juros Simples'),
        ('composto', 'Juros Compostos'),
    ]
    
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='emprestimos',
        verbose_name='Usuário Responsável'
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='emprestimos',
        verbose_name='Cliente'
    )
    valor = models.DecimalField(
        'Valor do Empréstimo (MT)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))],
        help_text='Valor mínimo: 100 MT'
    )
    taxa_juros = models.DecimalField(
        'Taxa de Juros (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Exemplo: 5.00 = 5%'
    )
    quantidade_parcelas = models.IntegerField(
        'Número de Parcelas',
        validators=[MinValueValidator(1)],
        help_text='Máximo 60 parcelas'
    )
    tipo_juros = models.CharField(
        'Tipo de Juros',
        max_length=10,
        choices=TIPO_JUROS_CHOICES,
        default='composto'
    )
    valor_parcela = models.DecimalField(
        'Valor da Parcela (MT)',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    data_contrato = models.DateField('Data do Contrato', auto_now_add=True)
    data_primeiro_vencimento = models.DateField('Data do Primeiro Vencimento')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ativo')
    observacoes = models.TextField('Observações', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Calcular valor da parcela automaticamente
        if self.valor and self.taxa_juros and self.quantidade_parcelas:
            if self.tipo_juros == 'simples':
                # Juros Simples: J = C * i * t
                total_juros = self.valor * (self.taxa_juros / 100) * self.quantidade_parcelas
                total = self.valor + total_juros
                self.valor_parcela = total / self.quantidade_parcelas
            else:
                # Juros Compostos (PRICE): parcelas fixas
                taxa_mensal = self.taxa_juros / 100
                if taxa_mensal == 0:
                    self.valor_parcela = self.valor / self.quantidade_parcelas
                else:
                    fator = (1 + taxa_mensal) ** self.quantidade_parcelas
                    self.valor_parcela = self.valor * (taxa_mensal * fator) / (fator - 1)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cliente.nome} - {self.valor:.2f} MT"
    
    class Meta:
        verbose_name = 'Empréstimo'
        verbose_name_plural = 'Empréstimos'
        ordering = ['-criado_em']


# ============================================
# 4. PARCELA
# ============================================
class Parcela(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('atrasado', 'Atrasado'),
    ]
    
    emprestimo = models.ForeignKey(
        Emprestimo,
        on_delete=models.CASCADE,
        related_name='parcelas',
        verbose_name='Empréstimo'
    )
    numero = models.IntegerField('Número da Parcela')
    valor = models.DecimalField('Valor (MT)', max_digits=12, decimal_places=2)
    data_vencimento = models.DateField('Data de Vencimento')
    data_pagamento = models.DateField('Data de Pagamento', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    
    def __str__(self):
        return f"Parcela {self.numero} - {self.emprestimo.cliente.nome}"
    
    class Meta:
        verbose_name = 'Parcela'
        verbose_name_plural = 'Parcelas'
        ordering = ['data_vencimento']


# ============================================
# 5. PAGAMENTO
# ============================================
class Pagamento(models.Model):
    FORMA_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('pix', 'PIX'),
        ('transferencia', 'Transferência Bancária'),
        ('cartao', 'Cartão de Débito/Crédito'),
        ('deposito', 'Depósito Bancário'),
        ('outros', 'Outros'),
    ]
    
    parcela = models.OneToOneField(
        Parcela,
        on_delete=models.CASCADE,
        related_name='pagamento',
        verbose_name='Parcela'
    )
    valor = models.DecimalField('Valor Pago (MT)', max_digits=12, decimal_places=2)
    forma_pagamento = models.CharField('Forma de Pagamento', max_length=20, choices=FORMA_CHOICES)
    data_pagamento = models.DateTimeField('Data do Pagamento', auto_now_add=True)
    comprovante = models.FileField(
        'Comprovante',
        upload_to='comprovantes/%Y/%m/',
        blank=True,
        null=True,
        help_text='JPG, PNG ou PDF (max 5MB)'
    )
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Atualizar status da parcela
        self.parcela.status = 'pago'
        self.parcela.data_pagamento = self.data_pagamento.date()
        self.parcela.save()
        
        # Verificar se todas as parcelas do empréstimo estão pagas
        todas_pagas = all(p.status == 'pago' for p in self.parcela.emprestimo.parcelas.all())
        if todas_pagas:
            self.parcela.emprestimo.status = 'pago'
            self.parcela.emprestimo.save()
    
    def __str__(self):
        return f"Pagamento - Parcela {self.parcela.numero} ({self.data_pagamento.strftime('%d/%m/%Y')})"
    
    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-data_pagamento']

#--------------Notificacoes------------------------------------------
# ============================================
# NOTIFICAÇÕES
# ============================================
class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('vencimento', 'Lembrete de Vencimento'),
        ('atraso', 'Alerta de Atraso'),
        ('cobranca', 'Alerta para Credor'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviado', 'Enviado'),
        ('falhou', 'Falhou'),
    ]
    
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='notificacoes')
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='notificacoes', null=True, blank=True)
    parcela = models.ForeignKey('Parcela', on_delete=models.CASCADE, related_name='notificacoes', null=True, blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    destinatario = models.CharField('Destinatário (telefone)', max_length=20)
    mensagem = models.TextField('Mensagem')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_envio = models.DateTimeField(auto_now_add=True)
    data_agendamento = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.destinatario} - {self.status}"
    
    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-data_envio']


# models.py

class ConfiguracaoNotificacao(models.Model):
    empresa = models.OneToOneField('Empresa', on_delete=models.CASCADE, related_name='config_notificacao')
    
    # Configurações WhatsApp (existentes)
    whatsapp_token = models.CharField('Token WhatsApp Business', max_length=255, blank=True, null=True)
    whatsapp_phone_id = models.CharField('Phone ID WhatsApp', max_length=255, blank=True, null=True)
    
    # Configurações SMS (existentes)
    sms_api_key = models.CharField('API Key SMS', max_length=255, blank=True, null=True)
    
    # Configurações de alertas por email (existentes)
    notificar_vencimento = models.BooleanField('Notificar vencimento', default=True)
    notificar_atraso = models.BooleanField('Notificar atraso', default=True)
    dias_antecedencia = models.IntegerField('Dias de antecedência', default=5)
    atraso_frequencia = models.IntegerField('Frequência de alertas em atraso (dias)', default=2)
    
    # ✅ NOVOS CAMPOS: Notificações Push (Popup no navegador)
    push_notificacoes_ativas = models.BooleanField('Ativar notificações push', default=True)
    push_alertar_vencimento = models.BooleanField('Alertar sobre parcelas próximas', default=True)
    push_alertar_atraso = models.BooleanField('Alertar sobre parcelas em atraso', default=True)
    push_dias_antecedencia = models.IntegerField('Dias de antecedência push', default=3)
    push_horario_inicio = models.TimeField('Horário início', default='08:00')
    push_horario_fim = models.TimeField('Horário fim', default='20:00')
    
    class Meta:
        verbose_name = 'Configuração de Notificação'
        verbose_name_plural = 'Configurações de Notificações'
    
    def __str__(self):
        return f"Configurações de {self.empresa.nome}"
#------------Classe Empresa--------------------------
# ============================================
# EMPRESA (NOVO - dados da empresa de microcrédito)
# ============================================
class Empresa(models.Model):
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('inativa', 'Inativa'),
        ('suspensa', 'Suspensa'),
        ('cancelada', 'Cancelada'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empresa')
    nome = models.CharField('Nome da Empresa', max_length=200)
    telefone = models.CharField('Telefone/WhatsApp', max_length=20, blank=True)
    email = models.EmailField('E-mail de Contato', blank=True)
    logo = models.ImageField('Logo da Empresa', upload_to='logos/%Y/%m/', blank=True, null=True)
    endereco = models.TextField('Endereço', blank=True)
    website = models.URLField('Website', blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ativa')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'


# PUSHWEB
# ============================================
# PUSH SUBSCRIPTION (Notificações Push)
# ============================================
class PushSubscription(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    subscription_info = models.JSONField('Informações da inscrição')
    is_active = models.BooleanField('Ativa', default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Push - {self.usuario.username}"
    
    class Meta:
        verbose_name = 'Inscrição Push'
        verbose_name_plural = 'Inscrições Push'
# firebase
class FCMToken(models.Model):
    """Modelo simples para armazenar tokens FCM"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=500, unique=True)
    device_type = models.CharField(max_length=20, default='web')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.token[:50]}..."


# FUNCIONÁRIO - CONTROLE DE PERMISSÕES
class Funcionario(models.Model):
    CARGO_CHOICES = [
        ('admin_empresa', 'Administrador da Empresa'),
        ('gerente', 'Gerente'),
        ('caixa', 'Caixa'),
        ('atendente', 'Atendente'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='funcionario')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='funcionarios')
    cargo = models.CharField('Cargo', max_length=20, choices=CARGO_CHOICES, default='atendente')
    pode_baixar_emprestimos = models.BooleanField('Pode baixar empréstimos', default=False)
    pode_regularizar_parcelas = models.BooleanField('Pode regularizar parcelas', default=False)
    pode_configurar_empresa = models.BooleanField('Pode configurar empresa', default=False)
    ativo = models.BooleanField('Ativo', default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nome} ({self.get_cargo_display()})"
    
    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
#============================================================================================
#modelo para verifcar emails
#============================================================================================
class EmailVerificacao(models.Model):
    """Modelo para gerenciar verificação de email de novos usuários"""
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verificacao_email')
    codigo = models.CharField('Código de verificação', max_length=100, unique=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    expira_em = models.DateTimeField('Expira em')
    verificado_em = models.DateTimeField('Verificado em', blank=True, null=True)
    
    def __str__(self):
        return f"{self.usuario.email} - {self.verificado_em and 'Verificado' or 'Pendente'}"
    
    def is_expired(self):
        """Verifica se o código já expirou"""
        from django.utils import timezone
        return timezone.now() > self.expira_em
    
    def is_verified(self):
        """Verifica se o email já foi confirmado"""
        return self.verificado_em is not None
    
    class Meta:
        verbose_name = 'Verificação de Email'
        verbose_name_plural = 'Verificações de Email'
        ordering = ['-criado_em']