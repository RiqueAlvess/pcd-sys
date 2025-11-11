"""
Django REST Framework serializers for Company users.

This module defines serializers for converting model instances to JSON
and validating incoming data.
"""

from rest_framework import serializers
from core.models import Empresa
from userpcd.models import Vaga, Candidatura
from .models import (
    EmpresaExtendida, VagaExtendida, ProcessoSeletivo, NotificacaoEmpresa
)


class EmpresaSerializer(serializers.ModelSerializer):
    """Serializer for Empresa model."""

    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Empresa
        fields = [
            'id', 'user', 'user_email', 'telefone_principal', 'telefone_secundario',
            'cnpj', 'razao_social', 'cnae_principal', 'tamanho', 'site', 'criado_em'
        ]
        read_only_fields = ['id', 'criado_em']


class EmpresaExtendidaSerializer(serializers.ModelSerializer):
    """Serializer for EmpresaExtendida model."""

    razao_social = serializers.CharField(source='empresa.razao_social', read_only=True)

    class Meta:
        model = EmpresaExtendida
        fields = [
            'id', 'empresa', 'razao_social', 'percentual_completude',
            'total_vagas_ativas', 'total_candidatos_recebidos'
        ]
        read_only_fields = [
            'id', 'percentual_completude', 'total_vagas_ativas',
            'total_candidatos_recebidos'
        ]


class VagaExtendidaSerializer(serializers.ModelSerializer):
    """Serializer for VagaExtendida model."""

    vaga_titulo = serializers.CharField(source='vaga.titulo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_medico_display = serializers.CharField(source='get_status_medico_display', read_only=True)

    class Meta:
        model = VagaExtendida
        fields = [
            'id', 'vaga', 'vaga_titulo', 'tipo', 'tipo_display', 'numero_vagas',
            'duracao_capacitacao', 'acesso_transporte_publico',
            'deficiencias_elegiveis', 'status_medico', 'status_medico_display',
            'observacoes_medicas', 'total_candidatos', 'candidatos_compativel'
        ]
        read_only_fields = ['id', 'total_candidatos', 'candidatos_compativel']


class ProcessoSeletivoSerializer(serializers.ModelSerializer):
    """Serializer for ProcessoSeletivo model."""

    candidato_nome = serializers.CharField(source='candidatura.pcd.nome_completo', read_only=True)
    vaga_titulo = serializers.CharField(source='candidatura.vaga.titulo', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProcessoSeletivo
        fields = [
            'id', 'candidatura', 'candidato_nome', 'vaga_titulo', 'status',
            'status_display', 'data_visualizacao_cv', 'data_contato',
            'data_entrevista', 'observacoes_empresa', 'atualizado_em'
        ]
        read_only_fields = ['id', 'atualizado_em']


class NotificacaoEmpresaSerializer(serializers.ModelSerializer):
    """Serializer for NotificacaoEmpresa model."""

    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    tempo_decorrido = serializers.SerializerMethodField()

    class Meta:
        model = NotificacaoEmpresa
        fields = [
            'id', 'empresa', 'tipo', 'tipo_display', 'titulo', 'mensagem',
            'vaga', 'candidatura', 'lida', 'criada_em', 'tempo_decorrido'
        ]
        read_only_fields = ['id', 'criada_em']

    def get_tempo_decorrido(self, obj):
        """Calculate time elapsed since notification was created."""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - obj.criada_em

        if diff < timedelta(minutes=1):
            return 'Agora mesmo'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} minuto{"s" if minutes > 1 else ""} atrás'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} hora{"s" if hours > 1 else ""} atrás'
        elif diff < timedelta(days=30):
            days = diff.days
            return f'{days} dia{"s" if days > 1 else ""} atrás'
        else:
            return obj.criada_em.strftime('%d/%m/%Y')


class CandidatoDetalheSerializer(serializers.ModelSerializer):
    """Detailed serializer for Candidatura with PCD profile information."""

    pcd_nome = serializers.CharField(source='pcd.nome_completo', read_only=True)
    pcd_email = serializers.EmailField(source='pcd.user.email', read_only=True)
    pcd_telefone = serializers.CharField(source='pcd.telefone', read_only=True)
    pcd_deficiencias = serializers.SerializerMethodField()
    vaga_titulo = serializers.CharField(source='vaga.titulo', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processo_seletivo = serializers.SerializerMethodField()

    class Meta:
        model = Candidatura
        fields = [
            'id', 'pcd', 'pcd_nome', 'pcd_email', 'pcd_telefone',
            'pcd_deficiencias', 'vaga', 'vaga_titulo', 'status',
            'status_display', 'data_candidatura', 'atualizada_em',
            'observacoes', 'processo_seletivo'
        ]
        read_only_fields = ['id', 'data_candidatura', 'atualizada_em']

    def get_pcd_deficiencias(self, obj):
        """Get list of candidate's disabilities."""
        return [d.nome for d in obj.pcd.deficiencias.all()]

    def get_processo_seletivo(self, obj):
        """Get selective process details."""
        try:
            processo = ProcessoSeletivo.objects.get(candidatura=obj)
            return ProcessoSeletivoSerializer(processo).data
        except ProcessoSeletivo.DoesNotExist:
            return None
