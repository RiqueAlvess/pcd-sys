from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from core.models import Empresa
from userpcd.models import Vaga, Candidatura
from .models import EmpresaExtendida, VagaExtendida, ProcessoSeletivo, NotificacaoEmpresa


@receiver(post_save, sender=Empresa)
def criar_empresa_extendida(sender, instance, created, **kwargs):
    """
    Cria automaticamente uma EmpresaExtendida quando uma Empresa é criada
    """
    if created:
        EmpresaExtendida.objects.get_or_create(
            empresa=instance,
            defaults={'percentual_completude': 60}
        )


@receiver(post_save, sender=Empresa)
def atualizar_completude_empresa(sender, instance, **kwargs):
    """
    Atualiza o percentual de completude sempre que a Empresa é modificada
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance)
        empresa_ext.calcular_completude()
    except EmpresaExtendida.DoesNotExist:
        # Criar empresa extendida se não existir
        empresa_ext = EmpresaExtendida.objects.create(
            empresa=instance,
            percentual_completude=60
        )
        empresa_ext.calcular_completude()


@receiver(post_save, sender=Vaga)
def criar_vaga_extendida(sender, instance, created, **kwargs):
    """
    Cria automaticamente uma VagaExtendida quando uma Vaga é criada
    """
    if created:
        VagaExtendida.objects.get_or_create(
            vaga=instance,
            defaults={
                'tipo': 'emprego',
                'numero_vagas': 1,
                'status_medico': 'pendente'
            }
        )


@receiver(post_save, sender=Candidatura)
def notificar_empresa_novo_candidato(sender, instance, created, **kwargs):
    """
    Notifica a empresa quando há uma nova candidatura
    """
    if created:
        NotificacaoEmpresa.objects.create(
            empresa=instance.vaga.empresa,
            tipo='novo_candidato',
            titulo='Nova Candidatura Recebida',
            mensagem=f'Você recebeu uma nova candidatura para a vaga "{instance.vaga.titulo}".',
            vaga=instance.vaga,
            candidatura=instance
        )
        
        # Atualizar contadores da vaga
        try:
            vaga_ext = VagaExtendida.objects.get(vaga=instance.vaga)
            vaga_ext.atualizar_contadores()
        except VagaExtendida.DoesNotExist:
            pass


@receiver(post_save, sender=Candidatura)
def criar_processo_seletivo(sender, instance, created, **kwargs):
    """
    Cria automaticamente um ProcessoSeletivo para cada candidatura
    """
    if created:
        ProcessoSeletivo.objects.get_or_create(
            candidatura=instance,
            defaults={'status': 'novo'}
        )


@receiver(post_save, sender=VagaExtendida)
def notificar_resultado_avaliacao_medica(sender, instance, **kwargs):
    """
    Notifica a empresa sobre mudanças no status da avaliação médica
    """
    # Verificar se o status médico mudou
    if instance.pk:
        try:
            old_instance = VagaExtendida.objects.get(pk=instance.pk)
            if hasattr(old_instance, '_state') and old_instance._state.db:
                # Comparar com versão anterior do banco
                old_status = VagaExtendida.objects.get(pk=instance.pk).status_medico
                if old_status != instance.status_medico:
                    _criar_notificacao_avaliacao_medica(instance)
        except VagaExtendida.DoesNotExist:
            # Primeiro save, criar notificação se não for pendente
            if instance.status_medico != 'pendente':
                _criar_notificacao_avaliacao_medica(instance)


def _criar_notificacao_avaliacao_medica(vaga_ext):
    """Helper para criar notificação de avaliação médica"""
    if vaga_ext.status_medico == 'aprovada':
        NotificacaoEmpresa.objects.create(
            empresa=vaga_ext.vaga.empresa,
            tipo='avaliacao_medica',
            titulo='Vaga Aprovada!',
            mensagem=f'Ótima notícia! Sua vaga "{vaga_ext.vaga.titulo}" foi aprovada pela equipe médica e já está recebendo candidaturas.',
            vaga=vaga_ext.vaga
        )
    elif vaga_ext.status_medico == 'rejeitada':
        mensagem = f'Sua vaga "{vaga_ext.vaga.titulo}" não foi aprovada pela equipe médica.'
        if vaga_ext.observacoes_medicas:
            mensagem += f' Motivo: {vaga_ext.observacoes_medicas}'
        mensagem += ' Você pode editar a vaga e reenviar para avaliação.'
        
        NotificacaoEmpresa.objects.create(
            empresa=vaga_ext.vaga.empresa,
            tipo='avaliacao_medica',
            titulo='Vaga Necessita Ajustes',
            mensagem=mensagem,
            vaga=vaga_ext.vaga
        )


@receiver(pre_save, sender=VagaExtendida)
def armazenar_status_anterior(sender, instance, **kwargs):
    """
    Armazena o status anterior para comparação no post_save
    """
    if instance.pk:
        try:
            old_instance = VagaExtendida.objects.get(pk=instance.pk)
            instance._old_status_medico = old_instance.status_medico
        except VagaExtendida.DoesNotExist:
            instance._old_status_medico = None
    else:
        instance._old_status_medico = None


@receiver(post_save, sender=VagaExtendida)
def notificar_mudanca_status_medico(sender, instance, created, **kwargs):
    """
    Notifica sobre mudanças no status médico (versão melhorada)
    """
    if not created and hasattr(instance, '_old_status_medico'):
        old_status = instance._old_status_medico
        new_status = instance.status_medico
        
        if old_status != new_status:
            if new_status == 'aprovada':
                NotificacaoEmpresa.objects.create(
                    empresa=instance.vaga.empresa,
                    tipo='avaliacao_medica',
                    titulo='🎉 Vaga Aprovada!',
                    mensagem=f'Excelente! Sua vaga "{instance.vaga.titulo}" foi aprovada pela equipe médica e já está ativa para receber candidaturas.',
                    vaga=instance.vaga
                )
            elif new_status == 'rejeitada':
                mensagem = f'Sua vaga "{instance.vaga.titulo}" precisa de alguns ajustes antes de ser publicada.'
                if instance.observacoes_medicas:
                    mensagem += f'\n\nObservações da equipe médica:\n{instance.observacoes_medicas}'
                mensagem += '\n\nVocê pode editar a vaga e reenviar para avaliação.'
                
                NotificacaoEmpresa.objects.create(
                    empresa=instance.vaga.empresa,
                    tipo='avaliacao_medica',
                    titulo='Vaga Necessita Ajustes',
                    mensagem=mensagem,
                    vaga=instance.vaga
                )


@receiver(post_save, sender=ProcessoSeletivo)
def atualizar_status_candidatura(sender, instance, **kwargs):
    """
    Sincroniza o status do processo seletivo com a candidatura
    """
    candidatura = instance.candidatura
    
    # Mapear status do processo para status da candidatura
    status_map = {
        'novo': 'pendente',
        'visualizado': 'em_analise',
        'contato_iniciado': 'em_analise',
        'entrevista_marcada': 'entrevista',
        'aprovado': 'aprovado',
        'rejeitado': 'rejeitado',
    }
    
    novo_status = status_map.get(instance.status, candidatura.status)
    
    if candidatura.status != novo_status:
        candidatura.status = novo_status
        candidatura.save()


@receiver(post_delete, sender=Vaga)
def limpar_vaga_extendida(sender, instance, **kwargs):
    """
    Remove a VagaExtendida quando a Vaga é deletada (caso necessário)
    """
    try:
        vaga_ext = VagaExtendida.objects.get(vaga=instance)
        vaga_ext.delete()
    except VagaExtendida.DoesNotExist:
        pass


@receiver(post_delete, sender=Empresa)
def limpar_empresa_extendida(sender, instance, **kwargs):
    """
    Remove a EmpresaExtendida quando a Empresa é deletada (caso necessário)
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance)
        empresa_ext.delete()
    except EmpresaExtendida.DoesNotExist:
        pass


# Signal para limpar notificações antigas automaticamente
def limpar_notificacoes_antigas_empresa():
    """
    Remove notificações mais antigas que 60 dias (pode ser chamado via cron job)
    """
    from django.utils import timezone
    from datetime import timedelta
    
    data_limite = timezone.now() - timedelta(days=60)
    notificacoes_antigas = NotificacaoEmpresa.objects.filter(
        criada_em__lt=data_limite,
        lida=True
    )
    
    count = notificacoes_antigas.count()
    notificacoes_antigas.delete()
    
    return f'{count} notificações antigas de empresas removidas'


# Signal para atualizar estatísticas das empresas
@receiver(post_save, sender=Vaga)
def atualizar_estatisticas_empresa(sender, instance, **kwargs):
    """
    Atualiza estatísticas da empresa quando vagas são criadas/modificadas
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance.empresa)
        
        # Contar vagas ativas
        vagas_ativas = Vaga.objects.filter(
            empresa=instance.empresa,
            status='ativa'
        ).count()
        
        # Contar total de candidatos
        total_candidatos = Candidatura.objects.filter(
            vaga__empresa=instance.empresa
        ).count()
        
        empresa_ext.total_vagas_ativas = vagas_ativas
        empresa_ext.total_candidatos_recebidos = total_candidatos
        empresa_ext.save()
        
    except EmpresaExtendida.DoesNotExist:
        pass


@receiver(post_delete, sender=Vaga)
def atualizar_estatisticas_empresa_delete(sender, instance, **kwargs):
    """
    Atualiza estatísticas da empresa quando vagas são deletadas
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance.empresa)
        
        # Recontar vagas ativas
        vagas_ativas = Vaga.objects.filter(
            empresa=instance.empresa,
            status='ativa'
        ).count()
        
        empresa_ext.total_vagas_ativas = vagas_ativas
        empresa_ext.save()
        
    except EmpresaExtendida.DoesNotExist:
        pass