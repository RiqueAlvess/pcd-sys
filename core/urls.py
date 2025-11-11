from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('escolha/', views.escolha_tipo, name='escolha_tipo'),
    path('cadastro/empresa/', views.cadastro_empresa, name='cadastro_empresa'),
    path('cadastro/pcd/', views.cadastro_pcd, name='cadastro_pcd'),
]