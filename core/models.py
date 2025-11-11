from django.db import models
from django.contrib.auth.models import User, AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('root', 'Root'),
        ('empresa', 'Empresa'),
        ('pcd', 'PCD'),
        ('medico', 'Médico'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    def is_root(self):
        return self.role == 'root'

    def is_empresa(self):
        return self.role == 'empresa'

    def is_pcd(self):
        return self.role == 'pcd'

    def is_medico(self):
        return self.role == 'medico'


class Empresa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone_principal = models.CharField(max_length=20)
    telefone_secundario = models.CharField(max_length=20, blank=True)
    cnpj = models.CharField(max_length=18, unique=True)
    razao_social = models.CharField(max_length=255)
    cnae_principal = models.CharField(max_length=10)
    tamanho = models.CharField(max_length=10)
    site = models.URLField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

class PCDProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    data_nascimento = models.DateField()
    cpf = models.CharField(max_length=14, unique=True)

    CATEGORIAS_DEFICIENCIA = [
        ('fisico', 'Físico/Motora'),
        ('auditiva', 'Auditiva'),
        ('visual', 'Visual'),
        ('intelectual', 'Intelectual/Psicológica'),
        ('multipla', 'Múltipla'),
    ]
    deficiencias = models.ManyToManyField('CategoriaDeficiencia', blank=True)

    nome_completo = models.CharField(max_length=255, blank=True)
    nome_mae = models.CharField(max_length=255, blank=True)
    endereco = models.TextField(blank=True)
    formacao_academica = models.TextField(blank=True)
    experiencia_profissional = models.TextField(blank=True)
    curriculo = models.FileField(upload_to='pcd/curriculos/', blank=True)
    laudos = models.FileField(upload_to='pcd/laudos/', blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

class CategoriaDeficiencia(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class MedicoProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nome_completo = models.CharField(max_length=255)
    crm = models.CharField(max_length=20)
    especialidade = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class ClassificacaoPCD(models.Model):
    """Modelo para classificação médica de PCD"""
    STATUS_CHOICES = [
        ('enquadravel', '✅ Enquadrável'),
        ('sugestivo', '⚠️ Sugestivo'),
        ('nao_enquadravel', '🚫 Não enquadrável'),
        ('avaliacao_adicional', '🩺 Avaliação adicional'),
        ('exame_necessario', '📄 Exame ou laudo necessário'),
    ]

    pcd = models.ForeignKey(PCDProfile, on_delete=models.CASCADE, related_name='classificacoes')
    medico = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classificacoes_realizadas')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    observacao = models.TextField(blank=True)
    documentos_analisados = models.TextField(blank=True, help_text='Lista de documentos que foram analisados')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Classificação PCD'
        verbose_name_plural = 'Classificações PCD'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.pcd.nome_completo} - {self.get_status_display()} ({self.medico.username})"
