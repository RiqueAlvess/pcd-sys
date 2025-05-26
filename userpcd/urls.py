from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_pcd, name='dashboard_pcd'),
    
    # Perfil
    path('perfil/editar/', views.editar_perfil_pcd, name='editar_perfil_pcd'),
    path('deficiencias/atualizar/', views.atualizar_deficiencias, name='atualizar_deficiencias'),
    
    # Documentos
    path('documento/upload/', views.upload_documento, name='upload_documento'),
    
    # Vagas
    path('vagas/', views.vagas_disponiveis, name='vagas_disponiveis'),
    path('candidatar/<int:vaga_id>/', views.candidatar_vaga, name='candidatar_vaga'),
    path('candidaturas/', views.minhas_candidaturas, name='minhas_candidaturas'),
    
    # Notificações
    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path('api/notificacoes/', views.notificacoes_dropdown, name='notificacoes_dropdown'),
]