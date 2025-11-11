"""
Django REST Framework API views for Company users.

This module provides RESTful API endpoints for:
- Notifications management (list, read, delete, mark as read)
- Candidatura management
- Job statistics
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import Empresa
from userpcd.models import Candidatura, Vaga
from .models import NotificacaoEmpresa, ProcessoSeletivo, VagaExtendida
from .serializers import (
    NotificacaoEmpresaSerializer, ProcessoSeletivoSerializer,
    CandidatoDetalheSerializer, VagaExtendidaSerializer
)


class NotificacaoEmpresaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for company notifications.

    Provides:
    - list: Get all notifications for current company
    - retrieve: Get specific notification
    - mark_as_read: Mark notification as read
    - mark_all_as_read: Mark all notifications as read
    - delete: Delete notification
    - unread_count: Get count of unread notifications
    """

    serializer_class = NotificacaoEmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter notifications by current company."""
        user = self.request.user
        if user.is_empresa():
            empresa = get_object_or_404(Empresa, user=user)
            return NotificacaoEmpresa.objects.filter(empresa=empresa).order_by('-criada_em')
        return NotificacaoEmpresa.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List all notifications for current company.

        Query params:
        - lida: Filter by read status (true/false)
        - tipo: Filter by type (novo_candidato, status_vaga, avaliacao_medica, sistema)
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

        POST /api/empresa/notificacoes/{id}/mark_as_read/
        """
        notificacao = self.get_object()
        notificacao.lida = True
        notificacao.save()

        # Update WebSocket counter
        from .tasks import atualizar_contador_notificacoes_empresa_task
        user = request.user
        empresa = get_object_or_404(Empresa, user=user)
        atualizar_contador_notificacoes_empresa_task.delay(empresa.id)

        return Response({
            'status': 'success',
            'message': 'Notificação marcada como lida'
        })

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        Mark all notifications as read.

        POST /api/empresa/notificacoes/mark_all_as_read/
        """
        count = self.get_queryset().filter(lida=False).update(lida=True)

        # Update WebSocket counter
        from .tasks import atualizar_contador_notificacoes_empresa_task
        user = request.user
        empresa = get_object_or_404(Empresa, user=user)
        atualizar_contador_notificacoes_empresa_task.delay(empresa.id)

        return Response({
            'status': 'success',
            'message': f'{count} notificações marcadas como lidas',
            'count': count
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications.

        GET /api/empresa/notificacoes/unread_count/
        """
        count = self.get_queryset().filter(lida=False).count()
        return Response({'count': count})

    def destroy(self, request, *args, **kwargs):
        """
        Delete notification.

        DELETE /api/empresa/notificacoes/{id}/
        """
        notificacao = self.get_object()
        notificacao.delete()

        # Update WebSocket counter
        from .tasks import atualizar_contador_notificacoes_empresa_task
        user = request.user
        empresa = get_object_or_404(Empresa, user=user)
        atualizar_contador_notificacoes_empresa_task.delay(empresa.id)

        return Response({
            'status': 'success',
            'message': 'Notificação excluída'
        }, status=status.HTTP_204_NO_CONTENT)


class CandidaturaEmpresaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for managing candidaturas (company view).

    Provides:
    - list: Get all candidaturas for company's jobs
    - retrieve: Get specific candidatura details
    - update_status: Update candidatura status
    """

    serializer_class = CandidatoDetalheSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter candidaturas by company's jobs."""
        user = self.request.user
        if user.is_empresa():
            empresa = get_object_or_404(Empresa, user=user)
            queryset = Candidatura.objects.filter(vaga__empresa=empresa).order_by('-data_candidatura')

            # Filter by vaga
            vaga_id = self.request.query_params.get('vaga')
            if vaga_id:
                queryset = queryset.filter(vaga_id=vaga_id)

            # Filter by status
            status_param = self.request.query_params.get('status')
            if status_param:
                queryset = queryset.filter(status=status_param)

            return queryset
        return Candidatura.objects.none()

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update candidatura status.

        POST /api/empresa/candidaturas/{id}/update_status/
        Body: {"status": "em_analise"|"entrevista"|"aprovado"|"rejeitado"}
        """
        candidatura = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = ['pendente', 'em_analise', 'entrevista', 'aprovado', 'rejeitado']
        if new_status not in valid_statuses:
            return Response({
                'status': 'error',
                'message': f'Status inválido. Use um dos seguintes: {", ".join(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        candidatura.status = new_status
        candidatura.save()

        # Update processo seletivo
        try:
            processo = ProcessoSeletivo.objects.get(candidatura=candidatura)

            # Map candidatura status to processo status
            status_map_reverse = {
                'pendente': 'novo',
                'em_analise': 'visualizado',
                'entrevista': 'entrevista_marcada',
                'aprovado': 'aprovado',
                'rejeitado': 'rejeitado',
            }

            processo.status = status_map_reverse.get(new_status, processo.status)

            # Update relevant dates
            if new_status == 'em_analise' and not processo.data_visualizacao_cv:
                processo.data_visualizacao_cv = timezone.now()
            elif new_status == 'entrevista' and not processo.data_entrevista:
                processo.data_entrevista = timezone.now()

            processo.save()
        except ProcessoSeletivo.DoesNotExist:
            pass

        return Response({
            'status': 'success',
            'message': 'Status atualizado com sucesso',
            'data': self.get_serializer(candidatura).data
        })

    @action(detail=True, methods=['post'])
    def add_observation(self, request, pk=None):
        """
        Add observation to candidatura.

        POST /api/empresa/candidaturas/{id}/add_observation/
        Body: {"observacao": "text"}
        """
        candidatura = self.get_object()
        observacao = request.data.get('observacao', '').strip()

        if not observacao:
            return Response({
                'status': 'error',
                'message': 'Observação não pode estar vazia'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Add to processo seletivo
        try:
            processo = ProcessoSeletivo.objects.get(candidatura=candidatura)
            if processo.observacoes_empresa:
                processo.observacoes_empresa += f'\n\n{observacao}'
            else:
                processo.observacoes_empresa = observacao
            processo.save()
        except ProcessoSeletivo.DoesNotExist:
            pass

        return Response({
            'status': 'success',
            'message': 'Observação adicionada com sucesso'
        })


class ProcessoSeletivoViewSet(viewsets.ModelViewSet):
    """
    API endpoint for selective process management.

    Provides:
    - list: Get all selective processes for company
    - retrieve: Get specific processo details
    - update: Update processo details
    """

    serializer_class = ProcessoSeletivoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter processos by company's jobs."""
        user = self.request.user
        if user.is_empresa():
            empresa = get_object_or_404(Empresa, user=user)
            return ProcessoSeletivo.objects.filter(
                candidatura__vaga__empresa=empresa
            ).order_by('-atualizado_em')
        return ProcessoSeletivo.objects.none()


class VagaExtendidaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for extended job information.

    Provides:
    - list: Get all extended jobs for company
    - retrieve: Get specific extended job details
    - update: Update extended job information
    - statistics: Get job statistics
    """

    serializer_class = VagaExtendidaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter extended jobs by company."""
        user = self.request.user
        if user.is_empresa():
            empresa = get_object_or_404(Empresa, user=user)
            return VagaExtendida.objects.filter(vaga__empresa=empresa)
        return VagaExtendida.objects.none()

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Get statistics for a specific job.

        GET /api/empresa/vagas-extendidas/{id}/statistics/
        """
        vaga_ext = self.get_object()

        # Update counters
        vaga_ext.atualizar_contadores()

        candidaturas = Candidatura.objects.filter(vaga=vaga_ext.vaga)

        stats = {
            'total_candidatos': vaga_ext.total_candidatos,
            'candidatos_compativel': vaga_ext.candidatos_compativel,
            'por_status': {
                'pendente': candidaturas.filter(status='pendente').count(),
                'em_analise': candidaturas.filter(status='em_analise').count(),
                'entrevista': candidaturas.filter(status='entrevista').count(),
                'aprovado': candidaturas.filter(status='aprovado').count(),
                'rejeitado': candidaturas.filter(status='rejeitado').count(),
            },
            'deficiencias_elegiveis': [d.nome for d in vaga_ext.deficiencias_elegiveis.all()],
            'status_medico': vaga_ext.get_status_medico_display(),
        }

        return Response(stats)
