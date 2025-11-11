"""
Celery tasks for PCD users.

This module contains asynchronous tasks for background processing.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task
def limpar_notificacoes_antigas_task() -> Dict[str, Any]:
    """
    Task to clean old read notifications (older than 30 days).

    Returns:
        Dict with count of deleted notifications
    """
    from userpcd.models import Notificacao

    data_limite = timezone.now() - timedelta(days=30)
    notificacoes_antigas = Notificacao.objects.filter(
        lida=True,
        criada_em__lt=data_limite
    )
    count = notificacoes_antigas.count()
    notificacoes_antigas.delete()

    return {
        'task': 'limpar_notificacoes_antigas_pcd',
        'deleted_count': count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def enviar_notificacao_websocket_task(user_id: int, notificacao_data: Dict[str, Any]):
    """
    Task to send notification via WebSocket.

    Args:
        user_id: ID of the user to notify
        notificacao_data: Notification data to send
    """
    channel_layer = get_channel_layer()
    room_group_name = f'notifications_pcd_{user_id}'

    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'notification_message',
            'notification': notificacao_data
        }
    )


@shared_task
def atualizar_contador_notificacoes_task(user_id: int):
    """
    Task to update unread notification count via WebSocket.

    Args:
        user_id: ID of the user
    """
    from userpcd.models import Notificacao
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        unread_count = Notificacao.objects.filter(user=user, lida=False).count()

        channel_layer = get_channel_layer()
        room_group_name = f'notifications_pcd_{user_id}'

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'unread_count_update',
                'count': unread_count
            }
        )
    except User.DoesNotExist:
        pass


@shared_task
def processar_upload_documento_task(documento_id: int):
    """
    Task to process document upload asynchronously.

    Args:
        documento_id: ID of the document to process
    """
    from userpcd.models import Documento

    try:
        documento = Documento.objects.get(id=documento_id)

        # Aqui você pode adicionar processamento adicional:
        # - Validação de PDF/imagem
        # - OCR do documento
        # - Detecção de informações
        # - Geração de thumbnail

        # Por enquanto, apenas marca como processado
        return {
            'documento_id': documento_id,
            'status': 'processed',
            'timestamp': timezone.now().isoformat()
        }
    except Documento.DoesNotExist:
        return {
            'documento_id': documento_id,
            'status': 'error',
            'message': 'Documento não encontrado'
        }


@shared_task
def calcular_compatibilidade_vagas_task(pcd_profile_id: int):
    """
    Task to calculate job compatibility for a PCD profile.

    Args:
        pcd_profile_id: ID of the PCD profile
    """
    from core.models import PCDProfile
    from userpcd.models import Vaga
    from usercompany.models import VagaExtendida

    try:
        pcd_profile = PCDProfile.objects.get(id=pcd_profile_id)
        deficiencias_pcd = set(pcd_profile.deficiencias.all())

        # Encontrar vagas compatíveis
        vagas_ativas = Vaga.objects.filter(status='ativa')
        vagas_compativeis = []

        for vaga in vagas_ativas:
            try:
                vaga_ext = vaga.vagaextendida
                deficiencias_elegiveis = set(vaga_ext.deficiencias_elegiveis.all())

                # Se não tem deficiências elegíveis, aceita todas
                if not deficiencias_elegiveis:
                    vagas_compativeis.append(vaga.id)
                # Se tem intersecção, é compatível
                elif deficiencias_pcd.intersection(deficiencias_elegiveis):
                    vagas_compativeis.append(vaga.id)
            except:
                pass

        return {
            'pcd_profile_id': pcd_profile_id,
            'vagas_compativeis': vagas_compativeis,
            'total': len(vagas_compativeis)
        }
    except PCDProfile.DoesNotExist:
        return {
            'pcd_profile_id': pcd_profile_id,
            'error': 'PCD Profile não encontrado'
        }
