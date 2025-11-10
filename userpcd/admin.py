from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from django.utils.html import format_html
from .models import Vaga, Candidatura, Documento, Notificacao, PerfilPCDExtendido, Conversa, Mensagem


@admin.register(Vaga)
class VagaAdmin(ModelAdmin):
    list_display = ['titulo', 'empresa', 'modalidade', 'cidade', 'uf', 'status', 'acessivel', 'criada_em']
    list_filter = ['modalidade', 'status', 'acessivel', 'criada_em', 'uf']
    search_fields = ['titulo', 'empresa__razao_social', 'cidade', 'descricao']
    list_editable = ['status', 'acessivel']
    date_hierarchy = 'criada_em'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'titulo', 'descricao')
        }),
        ('Localização', {
            'fields': ('modalidade', 'cidade', 'uf')
        }),
        ('Remuneração', {
            'fields': ('salario_min', 'salario_max'),
            'classes': ['collapse']
        }),
        ('Detalhes', {
            'fields': ('requisitos', 'beneficios', 'acessivel', 'status')
        }),
    )


@admin.register(Candidatura)
class CandidaturaAdmin(ModelAdmin):
    list_display = ['get_candidato', 'get_vaga_titulo', 'get_empresa', 'status', 'data_candidatura']
    list_filter = ['status', 'data_candidatura', 'vaga__modalidade']
    search_fields = ['pcd__user__username', 'pcd__nome_completo', 'vaga__titulo', 'vaga__empresa__razao_social']
    list_editable = ['status']
    date_hierarchy = 'data_candidatura'
    
    def get_candidato(self, obj):
        nome = obj.pcd.nome_completo or obj.pcd.user.username
        return format_html('<strong>{}</strong>', nome)
    get_candidato.short_description = 'Candidato'
    
    def get_vaga_titulo(self, obj):
        return obj.vaga.titulo
    get_vaga_titulo.short_description = 'Vaga'
    
    def get_empresa(self, obj):
        return obj.vaga.empresa.razao_social
    get_empresa.short_description = 'Empresa'


@admin.register(Documento)
class DocumentoAdmin(ModelAdmin):
    list_display = ['get_usuario', 'tipo', 'nome_original', 'status', 'data_upload']
    list_filter = ['tipo', 'status', 'data_upload']
    search_fields = ['pcd__user__username', 'pcd__nome_completo', 'nome_original', 'cid_10']
    list_editable = ['status']
    date_hierarchy = 'data_upload'
    
    def get_usuario(self, obj):
        nome = obj.pcd.nome_completo or obj.pcd.user.username
        return format_html('<strong>{}</strong>', nome)
    get_usuario.short_description = 'Usuário'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('pcd', 'tipo', 'arquivo', 'nome_original')
        }),
        ('Detalhes Médicos', {
            'fields': ('cid_10',),
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ('status', 'observacoes')
        }),
    )


@admin.register(Notificacao)
class NotificacaoAdmin(ModelAdmin):
    list_display = ['user', 'tipo', 'titulo', 'lida', 'criada_em']
    list_filter = ['tipo', 'lida', 'criada_em']
    search_fields = ['user__username', 'titulo', 'mensagem']
    list_editable = ['lida']
    date_hierarchy = 'criada_em'
    
    actions = ['marcar_como_lida', 'marcar_como_nao_lida']
    
    def marcar_como_lida(self, request, queryset):
        updated = queryset.update(lida=True)
        self.message_user(request, f'{updated} notificações marcadas como lidas.')
    marcar_como_lida.short_description = 'Marcar como lida'
    
    def marcar_como_nao_lida(self, request, queryset):
        updated = queryset.update(lida=False)
        self.message_user(request, f'{updated} notificações marcadas como não lidas.')
    marcar_como_nao_lida.short_description = 'Marcar como não lida'


@admin.register(PerfilPCDExtendido)
class PerfilPCDExtendidoAdmin(ModelAdmin):
    list_display = ['get_usuario', 'cidade', 'uf', 'status_medico', 'percentual_completude']
    list_filter = ['status_medico', 'uf', 'percentual_completude']
    search_fields = ['pcd_profile__user__username', 'pcd_profile__nome_completo', 'cidade']
    list_editable = ['status_medico']
    
    def get_usuario(self, obj):
        nome = obj.pcd_profile.nome_completo or obj.pcd_profile.user.username
        return format_html('<strong>{}</strong>', nome)
    get_usuario.short_description = 'Usuário'
    
    fieldsets = (
        ('Usuário', {
            'fields': ('pcd_profile',)
        }),
        ('Endereço', {
            'fields': ('cep', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'uf')
        }),
        ('Status', {
            'fields': ('status_medico', 'percentual_completude')
        }),
    )
    
    readonly_fields = ('percentual_completude',)
    
    actions = ['recalcular_completude']
    
    def recalcular_completude(self, request, queryset):
        updated = 0
        for perfil in queryset:
            perfil.calcular_completude()
            updated += 1
        self.message_user(request, f'Completude recalculada para {updated} perfis.')
    recalcular_completude.short_description = 'Recalcular % de completude'

@admin.register(Conversa)
class ConversaAdmin(ModelAdmin):
    list_display = ['get_pcd', 'get_empresa', 'get_vaga', 'criada_em', 'get_mensagens_count']
    list_filter = ['criada_em', 'atualizada_em']
    search_fields = ['pcd__user__username', 'pcd__nome_completo', 'empresa__razao_social', 'vaga__titulo']
    date_hierarchy = 'criada_em'
    
    def get_pcd(self, obj):
        nome = obj.pcd.nome_completo or obj.pcd.user.username
        return format_html('<strong>{}</strong>', nome)
    get_pcd.short_description = 'PCD'
    
    def get_empresa(self, obj):
        return format_html('<strong>{}</strong>', obj.empresa.razao_social)
    get_empresa.short_description = 'Empresa'
    
    def get_vaga(self, obj):
        return obj.vaga.titulo if obj.vaga else '-'
    get_vaga.short_description = 'Vaga'
    
    def get_mensagens_count(self, obj):
        return obj.mensagens.count()
    get_mensagens_count.short_description = 'Total de Mensagens'


@admin.register(Mensagem)
class MensagemAdmin(ModelAdmin):
    list_display = ['get_conversa', 'get_remetente', 'get_conteudo_resumido', 'lida', 'enviada_em']
    list_filter = ['remetente_empresa', 'lida', 'enviada_em']
    search_fields = ['conteudo', 'conversa__pcd__user__username', 'conversa__empresa__razao_social']
    date_hierarchy = 'enviada_em'
    list_editable = ['lida']
    
    def get_conversa(self, obj):
        pcd_nome = obj.conversa.pcd.nome_completo or obj.conversa.pcd.user.username
        return f"{pcd_nome} ↔ {obj.conversa.empresa.razao_social}"
    get_conversa.short_description = 'Conversa'
    
    def get_remetente(self, obj):
        if obj.remetente_empresa:
            return format_html('<span style="color: #16a34a;">📤 Empresa</span>')
        else:
            return format_html('<span style="color: #9333ea;">📥 PCD</span>')
    get_remetente.short_description = 'Remetente'
    
    def get_conteudo_resumido(self, obj):
        return obj.conteudo[:100] + '...' if len(obj.conteudo) > 100 else obj.conteudo
    get_conteudo_resumido.short_description = 'Conteúdo'
    
    actions = ['marcar_como_lida', 'marcar_como_nao_lida']
    
    def marcar_como_lida(self, request, queryset):
        updated = queryset.update(lida=True)
        self.message_user(request, f'{updated} mensagens marcadas como lidas.')
    marcar_como_lida.short_description = 'Marcar como lida'
    
    def marcar_como_nao_lida(self, request, queryset):
        updated = queryset.update(lida=False)
        self.message_user(request, f'{updated} mensagens marcadas como não lidas.')
    marcar_como_nao_lida.short_description = 'Marcar como não lida'
