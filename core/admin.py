# core/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import (
    User,
    Empresa,
    PCDProfile,
    MedicoProfile,
    CategoriaDeficiencia,
    ClassificacaoPCD,
)

# ---------- INLINES para anexar perfis ao usuário ---------- #

class EmpresaInline(admin.StackedInline):
    model = Empresa
    can_delete = False
    verbose_name_plural = "Dados da Empresa"
    fk_name = "user"
    fieldsets = (
        (None, {
            "fields": (
                ("cnpj", "razao_social"),
                ("telefone_principal", "telefone_secundario"),
                ("cnae_principal", "tamanho"),
                "site",
            )
        }),
    )

class PCDInline(admin.StackedInline):
    model = PCDProfile
    can_delete = False
    verbose_name_plural = "Dados do PCD"
    fk_name = "user"
    fieldsets = (
        (None, {
            "fields": (
                ("telefone", "cpf"),
                "data_nascimento",
                "deficiencias",
            )
        }),
    )
    filter_horizontal = ("deficiencias",)

class MedicoProfileInline(admin.StackedInline):
    model = MedicoProfile
    can_delete = False
    verbose_name_plural = "Dados do Médico"
    fk_name = "user"


# ----------------- USER ADMIN CUSTOMIZADO ------------------ #

@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    list_display  = ("username", "email", "role", "is_staff", "is_active")
    list_filter   = ("role", "is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email")
    ordering      = ("username",)

    fieldsets = (
        (None,               {"fields": ("username", "password")}),
        ("Informações Pessoais", {"fields": ("first_name", "last_name", "email")}),
        ("Permissões",       {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas Importantes",{"fields": ("last_login", "date_joined")}),
    )

    # Conecta os inlines corretos baseado no role
    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.role == "empresa":
                inlines = [EmpresaInline]
            elif obj.role == "pcd":
                inlines = [PCDInline]
            elif obj.role == "medico":
                inlines = [MedicoProfileInline]
        return [inline(self.model, self.admin_site) for inline in inlines]


# ----------------- OUTROS MODELOS SIMPLES ------------------ #

@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    list_display = ("id", "razao_social", "cnpj", "telefone_principal", "criado_em")
    search_fields = ("razao_social", "cnpj")
    list_filter = ("tamanho", "criado_em")
    readonly_fields = ("criado_em",)
    fieldsets = (
        ("Informações da Empresa", {
            "fields": ("user", "razao_social", "cnpj", "cnae_principal", "tamanho")
        }),
        ("Contatos", {
            "fields": ("telefone_principal", "telefone_secundario", "site")
        }),
        ("Datas", {
            "fields": ("criado_em",)
        }),
    )


@admin.register(PCDProfile)
class PCDProfileAdmin(ModelAdmin):
    list_display = ("id", "user", "nome_completo", "cpf", "data_nascimento", "telefone")
    search_fields = ("nome_completo", "cpf", "user__username", "user__email")
    list_filter = ("data_nascimento", "criado_em")
    readonly_fields = ("criado_em",)
    filter_horizontal = ("deficiencias",)
    fieldsets = (
        ("Informações do Usuário", {
            "fields": ("user", "nome_completo", "cpf", "data_nascimento")
        }),
        ("Contato", {
            "fields": ("telefone", "endereco")
        }),
        ("Dados da Deficiência", {
            "fields": ("deficiencias",)
        }),
        ("Informações Profissionais", {
            "fields": ("formacao_academica", "experiencia_profissional")
        }),
        ("Documentos", {
            "fields": ("curriculo", "laudos")
        }),
        ("Dados de Nome Social", {
            "fields": ("nome_mae",)
        }),
        ("Datas", {
            "fields": ("criado_em",)
        }),
    )


@admin.register(MedicoProfile)
class MedicoProfileAdmin(ModelAdmin):
    list_display = ("id", "user", "nome_completo", "crm", "especialidade", "criado_em")
    search_fields = ("nome_completo", "crm", "especialidade", "user__username", "user__email")
    list_filter = ("especialidade", "criado_em")
    readonly_fields = ("criado_em", "atualizado_em")
    fieldsets = (
        ("Informações do Médico", {
            "fields": ("user", "nome_completo", "crm", "especialidade")
        }),
        ("Datas", {
            "fields": ("criado_em", "atualizado_em")
        }),
    )


@admin.register(CategoriaDeficiencia)
class CategoriaDeficienciaAdmin(ModelAdmin):
    list_display  = ("nome",)
    search_fields = ("nome",)


@admin.register(ClassificacaoPCD)
class ClassificacaoPCDAdmin(ModelAdmin):
    list_display = ("pcd", "medico", "status", "criado_em")
    list_filter = ("status", ("criado_em", RangeDateFilter))
    search_fields = ("pcd__nome_completo", "pcd__cpf", "medico__username", "observacao")
    readonly_fields = ("criado_em", "atualizado_em")
    ordering = ("-criado_em",)

    fieldsets = (
        ("Informações Principais", {
            "fields": ("pcd", "medico", "status")
        }),
        ("Observações", {
            "fields": ("observacao", "documentos_analisados")
        }),
        ("Datas", {
            "fields": ("criado_em", "atualizado_em")
        }),
    )
