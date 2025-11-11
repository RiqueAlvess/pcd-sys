"""
Django REST Framework serializers for PCD users.

This module defines serializers for converting model instances to JSON
and validating incoming data.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import PCDProfile, CategoriaDeficiencia
from .models import (
    Vaga, Candidatura, Documento, Notificacao,
    PerfilPCDExtendido, Conversa, Mensagem
)

User = get_user_model()


class CategoriaDeficienciaSerializer(serializers.ModelSerializer):
    """Serializer for CategoriaDeficiencia model."""

    class Meta:
        model = CategoriaDeficiencia
        fields = ['id', 'nome']


class PCDProfileSerializer(serializers.ModelSerializer):
    """Serializer for PCDProfile model."""

    deficiencias = CategoriaDeficienciaSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = PCDProfile
        fields = [
            'id', 'user', 'user_email', 'telefone', 'cpf', 'data_nascimento',
            'nome_completo', 'nome_mae', 'endereco', 'formacao_academica',
            'experiencia_profissional', 'curriculo', 'laudos', 'deficiencias',
            'criado_em'
        ]
        read_only_fields = ['id', 'criado_em']


class VagaSerializer(serializers.ModelSerializer):
    """Serializer for Vaga model."""

    empresa_nome = serializers.CharField(source='empresa.razao_social', read_only=True)
    modalidade_display = serializers.CharField(source='get_modalidade_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Vaga
        fields = [
            'id', 'empresa', 'empresa_nome', 'titulo', 'descricao', 'requisitos',
            'beneficios', 'modalidade', 'modalidade_display', 'cidade', 'uf',
            'salario_min', 'salario_max', 'acessivel', 'status', 'status_display',
            'criada_em', 'atualizada_em'
        ]
        read_only_fields = ['id', 'criada_em', 'atualizada_em']


class CandidaturaSerializer(serializers.ModelSerializer):
    """Serializer for Candidatura model."""

    vaga_titulo = serializers.CharField(source='vaga.titulo', read_only=True)
    pcd_nome = serializers.CharField(source='pcd.nome_completo', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Candidatura
        fields = [
            'id', 'pcd', 'pcd_nome', 'vaga', 'vaga_titulo', 'status',
            'status_display', 'data_candidatura', 'atualizada_em', 'observacoes'
        ]
        read_only_fields = ['id', 'data_candidatura', 'atualizada_em']


class DocumentoSerializer(serializers.ModelSerializer):
    """Serializer for Documento model."""

    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Documento
        fields = [
            'id', 'pcd', 'tipo', 'tipo_display', 'arquivo', 'nome_original',
            'cid_10', 'status', 'status_display', 'data_upload', 'observacoes'
        ]
        read_only_fields = ['id', 'data_upload', 'nome_original']


class NotificacaoSerializer(serializers.ModelSerializer):
    """Serializer for Notificacao model."""

    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    tempo_decorrido = serializers.SerializerMethodField()

    class Meta:
        model = Notificacao
        fields = [
            'id', 'user', 'tipo', 'tipo_display', 'titulo', 'mensagem',
            'lida', 'criada_em', 'tempo_decorrido'
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


class PerfilPCDExtendidoSerializer(serializers.ModelSerializer):
    """Serializer for PerfilPCDExtendido model."""

    status_medico_display = serializers.CharField(source='get_status_medico_display', read_only=True)

    class Meta:
        model = PerfilPCDExtendido
        fields = [
            'id', 'pcd_profile', 'cep', 'rua', 'numero', 'complemento',
            'bairro', 'cidade', 'uf', 'status_medico', 'status_medico_display',
            'percentual_completude'
        ]
        read_only_fields = ['id', 'percentual_completude']


class MensagemSerializer(serializers.ModelSerializer):
    """Serializer for Mensagem model."""

    remetente = serializers.SerializerMethodField()

    class Meta:
        model = Mensagem
        fields = [
            'id', 'conversa', 'remetente_empresa', 'remetente', 'conteudo',
            'lida', 'enviada_em'
        ]
        read_only_fields = ['id', 'enviada_em']

    def get_remetente(self, obj):
        """Get sender name."""
        if obj.remetente_empresa:
            return obj.conversa.empresa.razao_social
        else:
            return obj.conversa.pcd.nome_completo


class ConversaSerializer(serializers.ModelSerializer):
    """Serializer for Conversa model."""

    ultima_mensagem = serializers.SerializerMethodField()
    mensagens_nao_lidas = serializers.SerializerMethodField()

    class Meta:
        model = Conversa
        fields = [
            'id', 'pcd', 'empresa', 'vaga', 'candidatura', 'criada_em',
            'atualizada_em', 'ultima_mensagem', 'mensagens_nao_lidas'
        ]
        read_only_fields = ['id', 'criada_em', 'atualizada_em']

    def get_ultima_mensagem(self, obj):
        """Get last message in conversation."""
        mensagem = obj.ultima_mensagem()
        if mensagem:
            return MensagemSerializer(mensagem).data
        return None

    def get_mensagens_nao_lidas(self, obj):
        """Get count of unread messages."""
        # Determine if request user is empresa or pcd
        request = self.context.get('request')
        if request and request.user:
            if request.user.is_empresa():
                return obj.mensagens_nao_lidas_empresa()
            else:
                return obj.mensagens_nao_lidas_pcd()
        return 0
