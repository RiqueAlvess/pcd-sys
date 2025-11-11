"""
Django signals for Company users.

This module handles automatic actions when models are created/updated:
- Creating extended profiles for companies and jobs
- Sending notifications (synchronous and via WebSocket)
- Managing selective processes
- Updating statistics
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from typing import Optional

from core.models import Empresa
from userpcd.models import Vaga, Candidatura
from .models import EmpresaExtendida, VagaExtendida, ProcessoSeletivo, NotificacaoEmpresa


@receiver(post_save, sender=Empresa)
def criar_empresa_extendida(sender, instance, created, **kwargs):
    """
    Automatically create EmpresaExtendida when Empresa is created.

    Args:
        sender: The model class (Empresa)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        EmpresaExtendida.objects.get_or_create(
            empresa=instance,
            defaults={'percentual_completude': 60}
        )
    else:
        # Ensure it exists even when updating
        EmpresaExtendida.objects.get_or_create(
            empresa=instance,
            defaults={'percentual_completude': 60}
        )


@receiver(post_save, sender=Empresa)
def atualizar_completude_empresa(sender, instance, **kwargs):
    """
    Update completion percentage whenever Empresa is modified.

    Args:
        sender: The model class (Empresa)
        instance: The actual instance being saved
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance)
        empresa_ext.calcular_completude()
    except EmpresaExtendida.DoesNotExist:
        # Create extended empresa if it doesn't exist
        empresa_ext = EmpresaExtendida.objects.create(
            empresa=instance,
            percentual_completude=60
        )
        empresa_ext.calcular_completude()


@receiver(post_save, sender=Vaga)
def criar_vaga_extendida(sender, instance, created, **kwargs):
    """
    Automatically create VagaExtendida when Vaga is created.

    Args:
        sender: The model class (Vaga)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        # Check if VagaExtendida already exists
        if not VagaExtendida.objects.filter(vaga=instance).exists():
            VagaExtendida.objects.create(
                vaga=instance,
                tipo='emprego',
                numero_vagas=1,
                status_medico='pendente'
            )


@receiver(post_save, sender=Candidatura)
def notificar_empresa_novo_candidato(sender, instance, created, **kwargs):
    """
    Notify company when there's a new candidatura.

    Args:
        sender: The model class (Candidatura)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        notificacao = NotificacaoEmpresa.objects.create(
            empresa=instance.vaga.empresa,
            tipo='novo_candidato',
            titulo='Nova Candidatura Recebida',
            mensagem=f'Você recebeu uma nova candidatura para a vaga "{instance.vaga.titulo}".',
            vaga=instance.vaga,
            candidatura=instance
        )

        # Send notification via WebSocket asynchronously
        enviar_notificacao_empresa_websocket(instance.vaga.empresa.id, notificacao)

        # Update job counters asynchronously
        from .tasks import atualizar_estatisticas_vaga_task
        atualizar_estatisticas_vaga_task.delay(instance.vaga.id)


@receiver(post_save, sender=Candidatura)
def criar_processo_seletivo(sender, instance, created, **kwargs):
    """
    Automatically create ProcessoSeletivo for each candidatura.

    Args:
        sender: The model class (Candidatura)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        ProcessoSeletivo.objects.get_or_create(
            candidatura=instance,
            defaults={'status': 'novo'}
        )


@receiver(pre_save, sender=VagaExtendida)
def armazenar_status_anterior(sender, instance, **kwargs):
    """
    Store previous status for comparison in post_save.

    Args:
        sender: The model class (VagaExtendida)
        instance: The actual instance being saved
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
    Notify about changes in medical status.

    Args:
        sender: The model class (VagaExtendida)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if not created and hasattr(instance, '_old_status_medico'):
        old_status = instance._old_status_medico
        new_status = instance.status_medico

        if old_status != new_status:
            notificacao = None

            if new_status == 'aprovada':
                notificacao = NotificacaoEmpresa.objects.create(
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

                notificacao = NotificacaoEmpresa.objects.create(
                    empresa=instance.vaga.empresa,
                    tipo='avaliacao_medica',
                    titulo='Vaga Necessita Ajustes',
                    mensagem=mensagem,
                    vaga=instance.vaga
                )

            if notificacao:
                # Send notification via WebSocket asynchronously
                enviar_notificacao_empresa_websocket(instance.vaga.empresa.id, notificacao)


@receiver(post_save, sender=ProcessoSeletivo)
def atualizar_status_candidatura(sender, instance, **kwargs):
    """
    Synchronize ProcessoSeletivo status with Candidatura.

    Args:
        sender: The model class (ProcessoSeletivo)
        instance: The actual instance being saved
    """
    candidatura = instance.candidatura

    # Map processo status to candidatura status
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
    Remove VagaExtendida when Vaga is deleted.

    Args:
        sender: The model class (Vaga)
        instance: The actual instance being deleted
    """
    try:
        vaga_ext = VagaExtendida.objects.get(vaga=instance)
        vaga_ext.delete()
    except VagaExtendida.DoesNotExist:
        pass


@receiver(post_delete, sender=Empresa)
def limpar_empresa_extendida(sender, instance, **kwargs):
    """
    Remove EmpresaExtendida when Empresa is deleted.

    Args:
        sender: The model class (Empresa)
        instance: The actual instance being deleted
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance)
        empresa_ext.delete()
    except EmpresaExtendida.DoesNotExist:
        pass


@receiver(post_save, sender=Vaga)
def atualizar_estatisticas_empresa(sender, instance, **kwargs):
    """
    Update company statistics when jobs are created/modified.

    Args:
        sender: The model class (Vaga)
        instance: The actual instance being saved
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance.empresa)

        # Count active jobs
        vagas_ativas = Vaga.objects.filter(
            empresa=instance.empresa,
            status='ativa'
        ).count()

        # Count total candidates
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
    Update company statistics when jobs are deleted.

    Args:
        sender: The model class (Vaga)
        instance: The actual instance being deleted
    """
    try:
        empresa_ext = EmpresaExtendida.objects.get(empresa=instance.empresa)

        # Recount active jobs
        vagas_ativas = Vaga.objects.filter(
            empresa=instance.empresa,
            status='ativa'
        ).count()

        empresa_ext.total_vagas_ativas = vagas_ativas
        empresa_ext.save()

    except EmpresaExtendida.DoesNotExist:
        pass


# Helper functions

def enviar_notificacao_empresa_websocket(empresa_id: int, notificacao: NotificacaoEmpresa):
    """
    Send notification to company via WebSocket asynchronously using Celery.

    Args:
        empresa_id: ID of the empresa to notify
        notificacao: NotificacaoEmpresa instance to send
    """
    from .tasks import enviar_notificacao_empresa_websocket_task, atualizar_contador_notificacoes_empresa_task

    notificacao_data = {
        'id': notificacao.id,
        'tipo': notificacao.tipo,
        'titulo': notificacao.titulo,
        'mensagem': notificacao.mensagem,
        'lida': notificacao.lida,
        'criada_em': notificacao.criada_em.isoformat(),
    }

    # Send notification via WebSocket
    enviar_notificacao_empresa_websocket_task.delay(empresa_id, notificacao_data)

    # Update unread count
    atualizar_contador_notificacoes_empresa_task.delay(empresa_id)


def limpar_notificacoes_antigas_empresa() -> str:
    """
    Remove old read notifications for companies (older than 60 days).
    Can be called via cron job or management command.

    Returns:
        Message indicating how many notifications were removed
    """
    data_limite = timezone.now() - timedelta(days=60)
    notificacoes_antigas = NotificacaoEmpresa.objects.filter(
        criada_em__lt=data_limite,
        lida=True
    )

    count = notificacoes_antigas.count()
    notificacoes_antigas.delete()

    return f'{count} notificações antigas de empresas removidas'
