# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import (
    User,
    Empresa,
    PCDProfile,
    MedicoProfile,
    CategoriaDeficiencia,
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
class UserAdmin(DjangoUserAdmin):
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

@admin.register(CategoriaDeficiencia)
class CategoriaDeficienciaAdmin(admin.ModelAdmin):
    list_display  = ("nome",)
    search_fields = ("nome",)
