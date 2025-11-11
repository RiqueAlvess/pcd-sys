"""
Celery tasks for Company users.

This module contains asynchronous tasks for background processing.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task
def limpar_notificacoes_antigas_empresa_task() -> Dict[str, Any]:
    """
    Task to clean old read notifications for companies (older than 60 days).

    Returns:
        Dict with count of deleted notifications
    """
    from usercompany.models import NotificacaoEmpresa

    data_limite = timezone.now() - timedelta(days=60)
    notificacoes_antigas = NotificacaoEmpresa.objects.filter(
        lida=True,
        criada_em__lt=data_limite
    )
    count = notificacoes_antigas.count()
    notificacoes_antigas.delete()

    return {
        'task': 'limpar_notificacoes_antigas_empresa',
        'deleted_count': count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def enviar_notificacao_empresa_websocket_task(empresa_id: int, notificacao_data: Dict[str, Any]):
    """
    Task to send notification to company via WebSocket.

    Args:
        empresa_id: ID of the empresa
        notificacao_data: Notification data to send
    """
    from core.models import Empresa

    try:
        empresa = Empresa.objects.get(id=empresa_id)
        user_id = empresa.user.id

        channel_layer = get_channel_layer()
        room_group_name = f'notifications_empresa_{user_id}'

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'notification': notificacao_data
            }
        )
    except Empresa.DoesNotExist:
        pass


@shared_task
def atualizar_contador_notificacoes_empresa_task(empresa_id: int):
    """
    Task to update unread notification count for company via WebSocket.

    Args:
        empresa_id: ID of the empresa
    """
    from usercompany.models import NotificacaoEmpresa
    from core.models import Empresa

    try:
        empresa = Empresa.objects.get(id=empresa_id)
        user_id = empresa.user.id
        unread_count = NotificacaoEmpresa.objects.filter(empresa=empresa, lida=False).count()

        channel_layer = get_channel_layer()
        room_group_name = f'notifications_empresa_{user_id}'

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'unread_count_update',
                'count': unread_count
            }
        )
    except Empresa.DoesNotExist:
        pass


@shared_task
def atualizar_estatisticas_vaga_task(vaga_id: int):
    """
    Task to update job statistics asynchronously.

    Args:
        vaga_id: ID of the vaga
    """
    from userpcd.models import Vaga, Candidatura
    from usercompany.models import VagaExtendida

    try:
        vaga = Vaga.objects.get(id=vaga_id)
        vaga_ext = VagaExtendida.objects.get(vaga=vaga)

        # Atualizar contadores
        total_candidatos = Candidatura.objects.filter(vaga=vaga).count()
        vaga_ext.total_candidatos = total_candidatos

        # Calcular candidatos compatíveis
        if vaga_ext.deficiencias_elegiveis.exists():
            candidatos_compativeis = Candidatura.objects.filter(
                vaga=vaga,
                pcd__deficiencias__in=vaga_ext.deficiencias_elegiveis.all()
            ).distinct().count()
            vaga_ext.candidatos_compativel = candidatos_compativeis
        else:
            vaga_ext.candidatos_compativel = total_candidatos

        vaga_ext.save()

        return {
            'vaga_id': vaga_id,
            'total_candidatos': total_candidatos,
            'candidatos_compativel': vaga_ext.candidatos_compativel
        }
    except (Vaga.DoesNotExist, VagaExtendida.DoesNotExist):
        return {
            'vaga_id': vaga_id,
            'error': 'Vaga não encontrada'
        }


@shared_task
def enviar_relatorio_semanal_empresa_task(empresa_id: int):
    """
    Task to send weekly report to company.

    Args:
        empresa_id: ID of the empresa
    """
    from core.models import Empresa
    from userpcd.models import Vaga, Candidatura
    from django.utils import timezone
    from datetime import timedelta

    try:
        empresa = Empresa.objects.get(id=empresa_id)

        # Estatísticas da semana
        uma_semana_atras = timezone.now() - timedelta(days=7)

        vagas_ativas = Vaga.objects.filter(empresa=empresa, status='ativa').count()
        novas_candidaturas = Candidatura.objects.filter(
            vaga__empresa=empresa,
            data_candidatura__gte=uma_semana_atras
        ).count()

        return {
            'empresa_id': empresa_id,
            'vagas_ativas': vagas_ativas,
            'novas_candidaturas': novas_candidaturas,
            'periodo': 'últimos 7 dias'
        }
    except Empresa.DoesNotExist:
        return {
            'empresa_id': empresa_id,
            'error': 'Empresa não encontrada'
        }
