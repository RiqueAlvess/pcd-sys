"""
URLs para o painel médico
"""
from django.urls import path
from usercompany import views_medico

urlpatterns = [
    # Dashboard
    path('dashboard/', views_medico.dashboard_medico, name='dashboard_medico'),

    # Avaliação de PCDs
    path('pcd/', views_medico.lista_pcd_pendentes, name='lista_pcd_pendentes'),
    path('pcd/<int:pcd_id>/', views_medico.avaliar_pcd, name='avaliar_pcd'),

    # Avaliação de Vagas
    path('vagas/', views_medico.vagas_pendentes, name='vagas_pendentes'),
    path('vagas/<int:vaga_id>/', views_medico.avaliar_vaga, name='avaliar_vaga'),

    # Histórico
    path('historico/', views_medico.historico_classificacoes, name='historico_classificacoes'),

    # Chat com Candidatos
    path('conversas/', views_medico.lista_conversas_medico, name='lista_conversas_medico'),
    path('chat/<int:conversa_id>/', views_medico.sala_chat_medico, name='sala_chat_medico'),
    path('chat/<int:conversa_id>/mensagens/', views_medico.buscar_mensagens_medico, name='buscar_mensagens_medico'),
    path('iniciar-conversa/<int:pcd_id>/', views_medico.iniciar_conversa_medico, name='iniciar_conversa_medico'),
]
