"""
Django signals for PCD users.

This module handles automatic actions when models are created/updated:
- Creating extended profiles
- Sending notifications (synchronous and via WebSocket)
- Cleaning up files
- Updating completion percentages
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from typing import Optional
from core.models import PCDProfile
from .models import PerfilPCDExtendido, Candidatura, Documento, Notificacao


@receiver(post_save, sender=PCDProfile)
def criar_perfil_extendido(sender, instance, created, **kwargs):
    """
    Automatically create PerfilPCDExtendido when PCDProfile is created.

    Args:
        sender: The model class (PCDProfile)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        PerfilPCDExtendido.objects.get_or_create(
            pcd_profile=instance,
            defaults={'percentual_completude': 50}
        )


@receiver(post_save, sender=PCDProfile)
def atualizar_completude_perfil(sender, instance, **kwargs):
    """
    Update completion percentage whenever PCDProfile is modified.

    Args:
        sender: The model class (PCDProfile)
        instance: The actual instance being saved
    """
    try:
        perfil_ext = PerfilPCDExtendido.objects.get(pcd_profile=instance)
        perfil_ext.calcular_completude()
    except PerfilPCDExtendido.DoesNotExist:
        # Create extended profile if it doesn't exist
        perfil_ext = PerfilPCDExtendido.objects.create(
            pcd_profile=instance,
            percentual_completude=50
        )
        perfil_ext.calcular_completude()


@receiver(post_save, sender=Candidatura)
def notificar_candidatura_enviada(sender, instance, created, **kwargs):
    """
    Create notification and send via WebSocket when a candidatura is submitted.

    Args:
        sender: The model class (Candidatura)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        notificacao = Notificacao.objects.create(
            user=instance.pcd.user,
            tipo='candidatura',
            titulo='Candidatura Enviada',
            mensagem=f'Sua candidatura para a vaga "{instance.vaga.titulo}" na empresa {instance.vaga.empresa.razao_social} foi enviada com sucesso!'
        )

        # Send notification via WebSocket asynchronously
        enviar_notificacao_websocket(instance.pcd.user.id, notificacao)


@receiver(post_save, sender=Candidatura)
def notificar_mudanca_status_candidatura(sender, instance, created, **kwargs):
    """
    Create notification when candidatura status changes.

    Args:
        sender: The model class (Candidatura)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if not created:  # Only for updates, not creation
        status_messages = {
            'em_analise': f'Sua candidatura para "{instance.vaga.titulo}" está sendo analisada pela empresa {instance.vaga.empresa.razao_social}.',
            'entrevista': f'🎉 Parabéns! Você foi selecionado(a) para entrevista na vaga "{instance.vaga.titulo}" da empresa {instance.vaga.empresa.razao_social}.',
            'aprovado': f'🎉 Excelente! Você foi aprovado(a) na vaga "{instance.vaga.titulo}" da empresa {instance.vaga.empresa.razao_social}. Aguarde o contato da empresa.',
            'rejeitado': f'Infelizmente, você não foi selecionado(a) para a vaga "{instance.vaga.titulo}" da empresa {instance.vaga.empresa.razao_social}. Continue tentando, há muitas oportunidades!'
        }

        if instance.status in status_messages:
            notificacao = Notificacao.objects.create(
                user=instance.pcd.user,
                tipo='candidatura',
                titulo=f'Candidatura - {instance.get_status_display()}',
                mensagem=status_messages[instance.status]
            )

            # Send notification via WebSocket asynchronously
            enviar_notificacao_websocket(instance.pcd.user.id, notificacao)


@receiver(post_save, sender=Documento)
def notificar_upload_documento(sender, instance, created, **kwargs):
    """
    Create notification when a document is uploaded.

    Args:
        sender: The model class (Documento)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        tipo_display = instance.get_tipo_display()
        notificacao = Notificacao.objects.create(
            user=instance.pcd.user,
            tipo='documento',
            titulo=f'{tipo_display} Enviado',
            mensagem=f'Seu {tipo_display.lower()} "{instance.nome_original}" foi enviado com sucesso e está sendo analisado.'
        )

        # Send notification via WebSocket asynchronously
        enviar_notificacao_websocket(instance.pcd.user.id, notificacao)

        # Process document asynchronously (if needed)
        from .tasks import processar_upload_documento_task
        processar_upload_documento_task.delay(instance.id)


@receiver(post_save, sender=Documento)
def notificar_status_documento(sender, instance, created, **kwargs):
    """
    Create notification when document status changes.

    Args:
        sender: The model class (Documento)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    if not created:  # Only for updates
        notificacao = None

        if instance.status == 'aprovado':
            notificacao = Notificacao.objects.create(
                user=instance.pcd.user,
                tipo='documento',
                titulo=f'{instance.get_tipo_display()} Aprovado',
                mensagem=f'Seu {instance.get_tipo_display().lower()} "{instance.nome_original}" foi aprovado!'
            )
        elif instance.status == 'rejeitado':
            mensagem = f'Seu {instance.get_tipo_display().lower()} "{instance.nome_original}" foi rejeitado.'
            if instance.observacoes:
                mensagem += f' Motivo: {instance.observacoes}'

            notificacao = Notificacao.objects.create(
                user=instance.pcd.user,
                tipo='documento',
                titulo=f'{instance.get_tipo_display()} Rejeitado',
                mensagem=mensagem
            )

        if notificacao:
            # Send notification via WebSocket asynchronously
            enviar_notificacao_websocket(instance.pcd.user.id, notificacao)


@receiver(post_delete, sender=Documento)
def limpar_arquivo_documento(sender, instance, **kwargs):
    """
    Remove file from disk when document is deleted.

    Args:
        sender: The model class (Documento)
        instance: The actual instance being deleted
    """
    if instance.arquivo:
        try:
            import os
            if os.path.isfile(instance.arquivo.path):
                os.remove(instance.arquivo.path)
        except Exception:
            # Silent failure if file cannot be removed
            pass


@receiver(post_save, sender=PerfilPCDExtendido)
def notificar_perfil_completo(sender, instance, **kwargs):
    """
    Create notification when profile reaches 100% completion.

    Args:
        sender: The model class (PerfilPCDExtendido)
        instance: The actual instance being saved
    """
    if instance.percentual_completude == 100:
        # Check if notification already exists
        existe_notificacao = Notificacao.objects.filter(
            user=instance.pcd_profile.user,
            tipo='sistema',
            titulo__contains='Perfil Completo'
        ).exists()

        if not existe_notificacao:
            notificacao = Notificacao.objects.create(
                user=instance.pcd_profile.user,
                tipo='sistema',
                titulo='🎉 Perfil 100% Completo!',
                mensagem='Parabéns! Seu perfil está completamente preenchido. Agora você tem acesso a todas as funcionalidades e maior visibilidade para as empresas.'
            )

            # Send notification via WebSocket asynchronously
            enviar_notificacao_websocket(instance.pcd_profile.user.id, notificacao)


# Helper functions

def enviar_notificacao_websocket(user_id: int, notificacao: Notificacao):
    """
    Send notification via WebSocket asynchronously using Celery.

    Args:
        user_id: ID of the user to notify
        notificacao: Notificacao instance to send
    """
    from .tasks import enviar_notificacao_websocket_task, atualizar_contador_notificacoes_task

    notificacao_data = {
        'id': notificacao.id,
        'tipo': notificacao.tipo,
        'titulo': notificacao.titulo,
        'mensagem': notificacao.mensagem,
        'lida': notificacao.lida,
        'criada_em': notificacao.criada_em.isoformat(),
    }

    # Send notification via WebSocket
    enviar_notificacao_websocket_task.delay(user_id, notificacao_data)

    # Update unread count
    atualizar_contador_notificacoes_task.delay(user_id)


def limpar_notificacoes_antigas() -> str:
    """
    Remove old read notifications (older than 30 days).
    Can be called via cron job or management command.

    Returns:
        Message indicating how many notifications were removed
    """
    data_limite = timezone.now() - timedelta(days=30)
    notificacoes_antigas = Notificacao.objects.filter(
        criada_em__lt=data_limite,
        lida=True
    )

    count = notificacoes_antigas.count()
    notificacoes_antigas.delete()

    return f'{count} notificações antigas removidas'
