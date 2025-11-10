from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from django.utils.html import format_html
from .models import EmpresaExtendida, VagaExtendida, ProcessoSeletivo, NotificacaoEmpresa
from userpcd.models import Vaga


@admin.register(EmpresaExtendida)
class EmpresaExtendidaAdmin(ModelAdmin):
    list_display = ['get_empresa', 'percentual_completude', 'total_vagas_ativas', 'total_candidatos_recebidos']
    list_filter = ['percentual_completude']
    search_fields = ['empresa__razao_social', 'empresa__cnpj']
    readonly_fields = ['percentual_completude', 'total_vagas_ativas', 'total_candidatos_recebidos']
    
    def get_empresa(self, obj):
        return format_html('<strong>{}</strong>', obj.empresa.razao_social)
    get_empresa.short_description = 'Empresa'
    
    actions = ['recalcular_completude']
    
    def recalcular_completude(self, request, queryset):
        updated = 0
        for empresa_ext in queryset:
            empresa_ext.calcular_completude()
            updated += 1
        self.message_user(request, f'Completude recalculada para {updated} empresas.')
    recalcular_completude.short_description = 'Recalcular % de completude'


@admin.register(VagaExtendida)
class VagaExtendidaAdmin(ModelAdmin):
    list_display = ['get_vaga_titulo', 'get_empresa', 'tipo', 'numero_vagas', 'status_medico', 'total_candidatos']
    list_filter = ['tipo', 'status_medico', 'acesso_transporte_publico']
    search_fields = ['vaga__titulo', 'vaga__empresa__razao_social']
    list_editable = ['status_medico']
    
    fieldsets = (
        ('Vaga', {
            'fields': ('vaga',)
        }),
        ('Configurações', {
            'fields': ('tipo', 'numero_vagas', 'duracao_capacitacao')
        }),
        ('Acessibilidade', {
            'fields': ('acesso_transporte_publico', 'deficiencias_elegiveis')
        }),
        ('Avaliação Médica', {
            'fields': ('status_medico', 'observacoes_medicas')
        }),
        ('Estatísticas', {
            'fields': ('total_candidatos', 'candidatos_compativel'),
            'classes': ['collapse']
        }),
    )
    
    filter_horizontal = ('deficiencias_elegiveis',)
    readonly_fields = ('total_candidatos', 'candidatos_compativel')
    
    def get_vaga_titulo(self, obj):
        return obj.vaga.titulo
    get_vaga_titulo.short_description = 'Vaga'
    
    def get_empresa(self, obj):
        return obj.vaga.empresa.razao_social
    get_empresa.short_description = 'Empresa'
    
    actions = ['aprovar_vagas', 'rejeitar_vagas', 'atualizar_contadores']
    
    def aprovar_vagas(self, request, queryset):
        updated = queryset.update(status_medico='aprovada')
        self.message_user(request, f'{updated} vagas aprovadas.')
    aprovar_vagas.short_description = 'Aprovar vagas selecionadas'
    
    def rejeitar_vagas(self, request, queryset):
        updated = queryset.update(status_medico='rejeitada')
        self.message_user(request, f'{updated} vagas rejeitadas.')
    rejeitar_vagas.short_description = 'Rejeitar vagas selecionadas'
    
    def atualizar_contadores(self, request, queryset):
        updated = 0
        for vaga_ext in queryset:
            vaga_ext.atualizar_contadores()
            updated += 1
        self.message_user(request, f'Contadores atualizados para {updated} vagas.')
    atualizar_contadores.short_description = 'Atualizar contadores de candidatos'


@admin.register(ProcessoSeletivo)
class ProcessoSeletivoAdmin(ModelAdmin):
    list_display = ['get_candidato', 'get_vaga', 'get_empresa', 'status', 'atualizado_em']
    list_filter = ['status', 'atualizado_em']
    search_fields = [
        'candidatura__pcd__user__username', 
        'candidatura__pcd__nome_completo',
        'candidatura__vaga__titulo',
        'candidatura__vaga__empresa__razao_social'
    ]
    list_editable = ['status']
    date_hierarchy = 'atualizado_em'
    
    fieldsets = (
        ('Candidatura', {
            'fields': ('candidatura',)
        }),
        ('Status do Processo', {
            'fields': ('status',)
        }),
        ('Datas Importantes', {
            'fields': ('data_visualizacao_cv', 'data_contato', 'data_entrevista'),
            'classes': ['collapse']
        }),
        ('Observações', {
            'fields': ('observacoes_empresa',)
        }),
    )
    
    readonly_fields = ('atualizado_em',)
    
    def get_candidato(self, obj):
        nome = obj.candidatura.pcd.nome_completo or obj.candidatura.pcd.user.username
        return format_html('<strong>{}</strong>', nome)
    get_candidato.short_description = 'Candidato'
    
    def get_vaga(self, obj):
        return obj.candidatura.vaga.titulo
    get_vaga.short_description = 'Vaga'
    
    def get_empresa(self, obj):
        return obj.candidatura.vaga.empresa.razao_social
    get_empresa.short_description = 'Empresa'


@admin.register(NotificacaoEmpresa)
class NotificacaoEmpresaAdmin(ModelAdmin):
    list_display = ['get_empresa', 'tipo', 'titulo', 'lida', 'criada_em']
    list_filter = ['tipo', 'lida', 'criada_em']
    search_fields = ['empresa__razao_social', 'titulo', 'mensagem']
    list_editable = ['lida']
    date_hierarchy = 'criada_em'
    
    fieldsets = (
        ('Empresa', {
            'fields': ('empresa',)
        }),
        ('Notificação', {
            'fields': ('tipo', 'titulo', 'mensagem', 'lida')
        }),
        ('Relacionamentos', {
            'fields': ('vaga', 'candidatura'),
            'classes': ['collapse']
        }),
    )
    
    def get_empresa(self, obj):
        return format_html('<strong>{}</strong>', obj.empresa.razao_social)
    get_empresa.short_description = 'Empresa'
    
    actions = ['marcar_como_lida', 'marcar_como_nao_lida']
    
    def marcar_como_lida(self, request, queryset):
        updated = queryset.update(lida=True)
        self.message_user(request, f'{updated} notificações marcadas como lidas.')
    marcar_como_lida.short_description = 'Marcar como lida'
    
    def marcar_como_nao_lida(self, request, queryset):
        updated = queryset.update(lida=False)
        self.message_user(request, f'{updated} notificações marcadas como não lidas.')
    marcar_como_nao_lida.short_description = 'Marcar como não lida'


# Inline para mostrar VagaExtendida no admin da Vaga
class VagaExtendidaInline(admin.StackedInline):
    model = VagaExtendida
    can_delete = False
    verbose_name_plural = "Informações Estendidas da Vaga"
    fieldsets = (
        ('Configurações', {
            'fields': ('tipo', 'numero_vagas', 'duracao_capacitacao')
        }),
        ('Acessibilidade', {
            'fields': ('acesso_transporte_publico', 'deficiencias_elegiveis')
        }),
        ('Avaliação Médica', {
            'fields': ('status_medico', 'observacoes_medicas')
        }),
    )
    filter_horizontal = ('deficiencias_elegiveis',)


# Registrar o inline na VagaAdmin se ela existir
try:
    from userpcd.admin import VagaAdmin
    # Adicionar o inline se a classe VagaAdmin existir
    if hasattr(VagaAdmin, 'inlines'):
        VagaAdmin.inlines = list(VagaAdmin.inlines) + [VagaExtendidaInline]
    else:
        VagaAdmin.inlines = [VagaExtendidaInline]
except ImportError:
    # Se VagaAdmin não existir no userpcd.admin, não faz nada
    pass