"""
API URL configuration for PCD users.

This module defines RESTful API routes for PCD features.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    NotificacaoViewSet, ConversaViewSet, VagaViewSet, CandidaturaViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'notificacoes', NotificacaoViewSet, basename='notificacao')
router.register(r'conversas', ConversaViewSet, basename='conversa')
router.register(r'vagas', VagaViewSet, basename='vaga')
router.register(r'candidaturas', CandidaturaViewSet, basename='candidatura')

app_name = 'userpcd_api'

urlpatterns = [
    path('', include(router.urls)),
]
