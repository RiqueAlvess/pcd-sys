from django.db import models
from django.utils import timezone
from core.models import User, PCDProfile, Empresa
import os


class Vaga(models.Model):
    MODALIDADE_CHOICES = [
        ('presencial', 'Presencial'),
        ('remoto', 'Remoto'),
        ('hibrido', 'Híbrido'),
    ]
    
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('pausada', 'Pausada'),
        ('encerrada', 'Encerrada'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='vagas')
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    modalidade = models.CharField(max_length=20, choices=MODALIDADE_CHOICES)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    salario_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salario_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    requisitos = models.TextField()
    beneficios = models.TextField(blank=True)
    acessivel = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativa')
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f"{self.titulo} - {self.empresa.razao_social}"


class Candidatura(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_analise', 'Em Análise'),
        ('entrevista', 'Entrevista Agendada'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    pcd = models.ForeignKey(PCDProfile, on_delete=models.CASCADE, related_name='candidaturas')
    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name='candidatos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_candidatura = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        unique_together = ['pcd', 'vaga']
        ordering = ['-data_candidatura']

    def __str__(self):
        return f"{self.pcd.user.username} - {self.vaga.titulo}"


class Documento(models.Model):
    TIPO_CHOICES = [
        ('curriculo', 'Currículo'),
        ('laudo', 'Laudo Médico'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    pcd = models.ForeignKey(PCDProfile, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    arquivo = models.FileField(upload_to='documentos/')
    nome_original = models.CharField(max_length=255)
    cid_10 = models.CharField(max_length=10, blank=True, help_text="Para laudos médicos")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_upload = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.pcd.user.username}"
    
    def delete(self, *args, **kwargs):
        # Remove arquivo do disco
        if self.arquivo and os.path.isfile(self.arquivo.path):
            os.remove(self.arquivo.path)
        super().delete(*args, **kwargs)


class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('candidatura', 'Candidatura'),
        ('documento', 'Documento'),
        ('sistema', 'Sistema'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f"{self.titulo} - {self.user.username}"


# Extensão do modelo PCDProfile para informações adicionais
class PerfilPCDExtendido(models.Model):
    STATUS_MEDICO_CHOICES = [
        ('pendente', 'Pendente'),
        ('enquadravel', 'Enquadrável'),
        ('sugestivo', 'Sugestivo'),
        ('nao_enquadravel', 'Não Enquadrável'),
    ]

    pcd_profile = models.OneToOneField(PCDProfile, on_delete=models.CASCADE, related_name='perfil_extendido')
    cep = models.CharField(max_length=9, blank=True)
    rua = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    status_medico = models.CharField(max_length=20, choices=STATUS_MEDICO_CHOICES, default='pendente')
    percentual_completude = models.IntegerField(default=50)
    
    def calcular_completude(self):
        """Calcula o percentual de completude do perfil"""
        campos_obrigatorios = [
            self.pcd_profile.nome_completo,
            self.pcd_profile.telefone,
            self.pcd_profile.cpf,
            self.pcd_profile.data_nascimento,
            self.cep,
            self.rua,
            self.cidade,
            self.uf,
        ]
        
        campos_preenchidos = sum(1 for campo in campos_obrigatorios if campo)
        tem_deficiencias = self.pcd_profile.deficiencias.exists()
        tem_curriculo = self.pcd_profile.documentos.filter(tipo='curriculo').exists()
        
        # Base: 80% para campos obrigatórios
        completude = (campos_preenchidos / len(campos_obrigatorios)) * 80
        
        # +10% para deficiências selecionadas
        if tem_deficiencias:
            completude += 10
            
        # +10% para currículo enviado
        if tem_curriculo:
            completude += 10
            
        self.percentual_completude = min(int(completude), 100)
        self.save()
        return self.percentual_completude


class Conversa(models.Model):
    """Conversa entre PCD e Empresa"""
    pcd = models.ForeignKey(PCDProfile, on_delete=models.CASCADE, related_name='conversas_pcd')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='conversas_empresa')
    vaga = models.ForeignKey(Vaga, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversas')
    candidatura = models.ForeignKey('Candidatura', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversas')
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-atualizada_em']
        unique_together = ['pcd', 'empresa', 'vaga']

    def __str__(self):
        return f"Conversa: {self.pcd.user.username} - {self.empresa.razao_social}"

    def mensagens_nao_lidas_pcd(self):
        """Retorna número de mensagens não lidas pelo PCD"""
        return self.mensagens.filter(remetente_empresa=True, lida=False).count()

    def mensagens_nao_lidas_empresa(self):
        """Retorna número de mensagens não lidas pela empresa"""
        return self.mensagens.filter(remetente_empresa=False, lida=False).count()

    def ultima_mensagem(self):
        """Retorna a última mensagem da conversa"""
        return self.mensagens.order_by('-enviada_em').first()


class Mensagem(models.Model):
    """Mensagem trocada entre PCD e Empresa"""
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    remetente_empresa = models.BooleanField(default=False, help_text="True se remetente é empresa, False se é PCD")
    conteudo = models.TextField()
    lida = models.BooleanField(default=False)
    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['enviada_em']

    def __str__(self):
        remetente = "Empresa" if self.remetente_empresa else "PCD"
        return f"{remetente}: {self.conteudo[:50]}..."

    def marcar_como_lida(self):
        """Marca a mensagem como lida"""
        if not self.lida:
            self.lida = True
            self.save()