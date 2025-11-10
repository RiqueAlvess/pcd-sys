from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('escolha/', views.escolha_tipo, name='escolha_tipo'),
    path('cadastro/empresa/', views.cadastro_empresa, name='cadastro_empresa'),
    path('cadastro/pcd/', views.cadastro_pcd, name='cadastro_pcd'),

    # URLs Médico
    path('medico/dashboard/', views.dashboard_medico, name='dashboard_medico'),
    path('medico/pcds/', views.listar_pcds_pendentes, name='listar_pcds_pendentes'),
    path('medico/pcds/<int:pcd_id>/avaliar/', views.avaliar_pcd, name='avaliar_pcd'),
    path('medico/vagas/', views.listar_vagas_pendentes, name='listar_vagas_pendentes'),
    path('medico/vagas/<int:vaga_id>/avaliar/', views.avaliar_vaga, name='avaliar_vaga'),
]