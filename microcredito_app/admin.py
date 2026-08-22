from django.contrib import admin
from .models import PerfilUsuario, Cliente, Emprestimo, Parcela, Pagamento, Empresa, Notificacao, ConfiguracaoNotificacao, Plano

admin.site.register(PerfilUsuario)
admin.site.register(Cliente)
admin.site.register(Emprestimo)
admin.site.register(Parcela)
admin.site.register(Plano)
admin.site.register(Pagamento)
admin.site.register(Empresa)
admin.site.register(Notificacao)
admin.site.register(ConfiguracaoNotificacao)
#========================================================================
