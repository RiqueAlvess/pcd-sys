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
]