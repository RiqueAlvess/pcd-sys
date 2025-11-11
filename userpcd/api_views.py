"""
Django REST Framework API views for PCD users.

This module provides RESTful API endpoints for:
- Notifications management (list, read, delete, mark as read)
- Chat messages
- Profile management
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Notificacao, Conversa, Mensagem, Candidatura, Vaga
from .serializers import (
    NotificacaoSerializer, ConversaSerializer, MensagemSerializer,
    CandidaturaSerializer, VagaSerializer
)


class NotificacaoViewSet(viewsets.ModelViewSet):
    """
    API endpoint for PCD notifications.

    Provides:
    - list: Get all notifications for current user
    - retrieve: Get specific notification
    - mark_as_read: Mark notification as read
    - mark_all_as_read: Mark all notifications as read
    - delete: Delete notification
    - unread_count: Get count of unread notifications
    """

    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter notifications by current user."""
        return Notificacao.objects.filter(user=self.request.user).order_by('-criada_em')

    def list(self, request, *args, **kwargs):
        """
        List all notifications for current user.

        Query params:
        - lida: Filter by read status (true/false)
        - tipo: Filter by type (candidatura, documento, sistema)
        - limit: Limit number of results
        """
        queryset = self.get_queryset()

        # Filter by read status
        lida = request.query_params.get('lida')
        if lida is not None:
            lida_bool = lida.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(lida=lida_bool)

        # Filter by type
        tipo = request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        # Limit results
        limit = request.query_params.get('limit')
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'unread_count': self.get_queryset().filter(lida=False).count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark specific notification as read.

        POST /api/notificacoes/{id}/mark_as_read/
        """
        notificacao = self.get_object()
        notificacao.lida = True
        notificacao.save()

        # Update WebSocket counter
        from .tasks import atualizar_contador_notificacoes_task
        atualizar_contador_notificacoes_task.delay(request.user.id)

        return Response({
            'status': 'success',
            'message': 'Notificação marcada como lida'
        })

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        Mark all notifications as read.

        POST /api/notificacoes/mark_all_as_read/
        """
        count = self.get_queryset().filter(lida=False).update(lida=True)

        # Update WebSocket counter
        from .tasks import atualizar_contador_notificacoes_task
        atualizar_contador_notificacoes_task.delay(request.user.id)

        return Response({
            'status': 'success',
            'message': f'{count} notificações marcadas como lidas',
            'count': count
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications.

        GET /api/notificacoes/unread_count/
        """
        count = self.get_queryset().filter(lida=False).count()
        return Response({'count': count})

    def destroy(self, request, *args, **kwargs):
        """
        Delete notification.

        DELETE /api/notificacoes/{id}/
        """
        notificacao = self.get_object()
        notificacao.delete()

        # Update WebSocket counter
        from .tasks import atualizar_contador_notificacoes_task
        atualizar_contador_notificacoes_task.delay(request.user.id)

        return Response({
            'status': 'success',
            'message': 'Notificação excluída'
        }, status=status.HTTP_204_NO_CONTENT)


class ConversaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for chat conversations.

    Provides:
    - list: Get all conversations for current user
    - retrieve: Get specific conversation with messages
    - send_message: Send message in conversation
    """

    serializer_class = ConversaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter conversations by current user."""
        user = self.request.user
        if user.is_pcd():
            from core.models import PCDProfile
            pcd = get_object_or_404(PCDProfile, user=user)
            return Conversa.objects.filter(pcd=pcd).order_by('-atualizada_em')
        return Conversa.objects.none()

    def retrieve(self, request, *args, **kwargs):
        """
        Get conversation with messages.

        GET /api/conversas/{id}/
        """
        conversa = self.get_object()
        mensagens = conversa.mensagem_set.all().order_by('enviada_em')

        # Mark messages as read
        if request.user.is_pcd():
            mensagens.filter(remetente_empresa=True, lida=False).update(lida=True)

        return Response({
            'conversa': self.get_serializer(conversa).data,
            'mensagens': MensagemSerializer(mensagens, many=True).data
        })

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Send message in conversation.

        POST /api/conversas/{id}/send_message/
        Body: {"conteudo": "message text"}
        """
        conversa = self.get_object()
        conteudo = request.data.get('conteudo', '').strip()

        if not conteudo:
            return Response({
                'status': 'error',
                'message': 'Conteúdo da mensagem não pode estar vazio'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create message
        mensagem = Mensagem.objects.create(
            conversa=conversa,
            remetente_empresa=False,  # PCD is sending
            conteudo=conteudo,
            lida=False
        )

        # Send via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        room_group_name = f'chat_pcd_{conversa.pcd.id}_empresa_{conversa.empresa.id}_vaga_{conversa.vaga.id}'

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': mensagem.conteudo,
                'sender': request.user.email,
                'timestamp': mensagem.enviada_em.isoformat(),
                'is_empresa': False,
            }
        )

        return Response({
            'status': 'success',
            'message': 'Mensagem enviada',
            'data': MensagemSerializer(mensagem).data
        }, status=status.HTTP_201_CREATED)


class VagaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for job listings (read-only for PCDs).

    Provides:
    - list: Get all active jobs
    - retrieve: Get specific job details
    - candidatar: Apply to job
    """

    serializer_class = VagaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get all active jobs."""
        queryset = Vaga.objects.filter(status='ativa').order_by('-criada_em')

        # Filter by modalidade
        modalidade = self.request.query_params.get('modalidade')
        if modalidade:
            queryset = queryset.filter(modalidade=modalidade)

        # Filter by cidade
        cidade = self.request.query_params.get('cidade')
        if cidade:
            queryset = queryset.filter(cidade__icontains=cidade)

        # Filter by uf
        uf = self.request.query_params.get('uf')
        if uf:
            queryset = queryset.filter(uf=uf)

        return queryset

    @action(detail=True, methods=['post'])
    def candidatar(self, request, pk=None):
        """
        Apply to job.

        POST /api/vagas/{id}/candidatar/
        """
        vaga = self.get_object()
        user = request.user

        if not user.is_pcd():
            return Response({
                'status': 'error',
                'message': 'Apenas PCDs podem se candidatar a vagas'
            }, status=status.HTTP_403_FORBIDDEN)

        from core.models import PCDProfile
        pcd = get_object_or_404(PCDProfile, user=user)

        # Check if already applied
        if Candidatura.objects.filter(pcd=pcd, vaga=vaga).exists():
            return Response({
                'status': 'error',
                'message': 'Você já se candidatou a esta vaga'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create candidatura
        candidatura = Candidatura.objects.create(
            pcd=pcd,
            vaga=vaga,
            status='pendente'
        )

        return Response({
            'status': 'success',
            'message': 'Candidatura enviada com sucesso!',
            'data': CandidaturaSerializer(candidatura).data
        }, status=status.HTTP_201_CREATED)


class CandidaturaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for candidaturas (read-only for PCDs).

    Provides:
    - list: Get all candidaturas for current user
    - retrieve: Get specific candidatura details
    """

    serializer_class = CandidaturaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter candidaturas by current user."""
        user = self.request.user
        if user.is_pcd():
            from core.models import PCDProfile
            pcd = get_object_or_404(PCDProfile, user=user)
            return Candidatura.objects.filter(pcd=pcd).order_by('-data_candidatura')
        return Candidatura.objects.none()
