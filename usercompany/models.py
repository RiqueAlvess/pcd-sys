from django.db import models
from django.utils import timezone
from core.models import Empresa
from userpcd.models import Vaga, Candidatura


class EmpresaExtendida(models.Model):
    """Extensão do modelo Empresa com dados adicionais"""
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='empresa_extendida')
    percentual_completude = models.IntegerField(default=60)
    total_vagas_ativas = models.IntegerField(default=0)
    total_candidatos_recebidos = models.IntegerField(default=0)
    
    def calcular_completude(self):
        """Calcula o percentual de completude do perfil da empresa"""
        empresa = self.empresa
        
        campos_obrigatorios = [
            empresa.telefone_principal,
            empresa.cnpj, 
            empresa.razao_social,
            empresa.cnae_principal,
            empresa.tamanho,
        ]
        
        campos_preenchidos = sum(1 for campo in campos_obrigatorios if campo)
        
        # Base: 80% para campos obrigatórios
        completude = (campos_preenchidos / len(campos_obrigatorios)) * 80
        
        # +10% para telefone secundário
        if empresa.telefone_secundario:
            completude += 10
            
        # +10% para site
        if empresa.site:
            completude += 10
            
        self.percentual_completude = min(int(completude), 100)
        self.save()
        return self.percentual_completude

    def __str__(self):
        return f"Extensão - {self.empresa.razao_social}"


class VagaExtendida(models.Model):
    """Campos adicionais para vagas"""
    
    TIPO_CHOICES = [
        ('emprego', 'Emprego'),
        ('capacitacao', 'Capacitação'),
    ]
    
    STATUS_MEDICO_CHOICES = [
        ('pendente', 'Aguardando Avaliação'),
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
    ]
    
    vaga = models.OneToOneField(Vaga, on_delete=models.CASCADE, related_name='vaga_extendida')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='emprego')
    numero_vagas = models.IntegerField(default=1, help_text="Número de vagas disponíveis")
    duracao_capacitacao = models.CharField(max_length=100, blank=True, help_text="Para capacitações")
    
    # Acessibilidade
    acesso_transporte_publico = models.BooleanField(default=False)
    deficiencias_elegiveis = models.ManyToManyField('core.CategoriaDeficiencia', blank=True)
    
    # Status médico
    status_medico = models.CharField(max_length=20, choices=STATUS_MEDICO_CHOICES, default='pendente')
    observacoes_medicas = models.TextField(blank=True)
    
    # Contadores
    total_candidatos = models.IntegerField(default=0)
    candidatos_compativel = models.IntegerField(default=0)
    
    def atualizar_contadores(self):
        """Atualiza contadores de candidatos"""
        self.total_candidatos = self.vaga.candidatos.count()
        # Candidatos compatíveis = aqueles com deficiências elegíveis
        if self.deficiencias_elegiveis.exists():
            candidatos_compativeis = self.vaga.candidatos.filter(
                pcd__deficiencias__in=self.deficiencias_elegiveis.all()
            ).distinct().count()
            self.candidatos_compativel = candidatos_compativeis
        else:
            self.candidatos_compativel = self.total_candidatos
        self.save()

    def __str__(self):
        return f"Extensão - {self.vaga.titulo}"


class ProcessoSeletivo(models.Model):
    """Gerencia o processo seletivo de cada candidato"""
    
    STATUS_CHOICES = [
        ('novo', 'Novo Candidato'),
        ('visualizado', 'Currículo Visualizado'),
        ('contato_iniciado', 'Contato Iniciado'),
        ('entrevista_marcada', 'Entrevista Marcada'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    
    candidatura = models.OneToOneField(Candidatura, on_delete=models.CASCADE, related_name='processo_seletivo')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='novo')
    data_visualizacao_cv = models.DateTimeField(null=True, blank=True)
    data_contato = models.DateTimeField(null=True, blank=True)
    data_entrevista = models.DateTimeField(null=True, blank=True)
    observacoes_empresa = models.TextField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-atualizado_em']

    def __str__(self):
        return f"Processo - {self.candidatura.pcd.user.username} - {self.candidatura.vaga.titulo}"


class NotificacaoEmpresa(models.Model):
    """Notificações específicas para empresas"""
    
    TIPO_CHOICES = [
        ('novo_candidato', 'Novo Candidato'),
        ('status_vaga', 'Status da Vaga'),
        ('avaliacao_medica', 'Avaliação Médica'),
        ('sistema', 'Sistema'),
    ]
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='notificacoes_empresa')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, null=True, blank=True)
    candidatura = models.ForeignKey(Candidatura, on_delete=models.CASCADE, null=True, blank=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f"{self.titulo} - {self.empresa.razao_social}"
  