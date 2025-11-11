"""
API URL configuration for Company users.

This module defines RESTful API routes for Company features.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    NotificacaoEmpresaViewSet, CandidaturaEmpresaViewSet,
    ProcessoSeletivoViewSet, VagaExtendidaViewSet, ConversaEmpresaViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'notificacoes', NotificacaoEmpresaViewSet, basename='notificacao-empresa')
router.register(r'candidaturas', CandidaturaEmpresaViewSet, basename='candidatura-empresa')
router.register(r'processos-seletivos', ProcessoSeletivoViewSet, basename='processo-seletivo')
router.register(r'vagas-extendidas', VagaExtendidaViewSet, basename='vaga-extendida')
router.register(r'conversas', ConversaEmpresaViewSet, basename='conversa-empresa')

app_name = 'usercompany_api'

urlpatterns = [
    path('', include(router.urls)),
]
