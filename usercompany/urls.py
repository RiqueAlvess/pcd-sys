from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_empresa, name='dashboard_empresa'),

    # Perfil da empresa
    path('perfil/editar/', views.editar_perfil_empresa, name='editar_perfil_empresa'),

    # Gestão de vagas
    path('vagas/', views.minhas_vagas, name='minhas_vagas'),
    path('vagas/nova/', views.nova_vaga, name='nova_vaga'),
    path('vagas/<int:vaga_id>/', views.detalhes_vaga, name='detalhes_vaga'),
    path('vagas/<int:vaga_id>/editar/', views.editar_vaga, name='editar_vaga'),
    path('vagas/<int:vaga_id>/encerrar/', views.encerrar_vaga, name='encerrar_vaga'),

    # Gestão de candidatos
    path('vagas/<int:vaga_id>/candidatos/', views.candidatos_vaga, name='candidatos_vaga'),
    path('candidatos/<int:candidatura_id>/status/', views.atualizar_status_candidato, name='atualizar_status_candidato'),
    path('candidatos/<int:candidatura_id>/curriculo/', views.visualizar_curriculo, name='visualizar_curriculo'),

    # Notificações
    path('notificacoes/', views.notificacoes_empresa, name='notificacoes_empresa'),
    path('api/notificacoes/', views.notificacoes_dropdown_empresa, name='notificacoes_dropdown_empresa'),

    # Chat
    path('chat/', views.lista_conversas_empresa, name='lista_conversas_empresa'),
    path('chat/<int:conversa_id>/', views.sala_chat_empresa, name='sala_chat_empresa'),
]