from django.urls import path
from django.contrib.auth import views as auth_views # Importamos o motor de login do Django
from . import views

urlpatterns = [
    # Página inicial
    path('', views.home, name='home'),
    
    # Páginas de Login e Logout
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Nova página de Adicionar Carro
    path('novo-carro/', views.add_vehicle, name='add_vehicle'),
    # Rota Dinâmica
    path('editar-carro/<int:id>/', views.edit_vehicle, name='edit_vehicle'),
    path('excluir-carro/<int:id>/', views.delete_vehicle, name='delete_vehicle'),
    # Página de Registro
    path('registrar/', views.register, name='register'),
    # Rota para solicitar manutenção
    path('solicitar-manutencao/', views.request_maintenance, name='request_maintenance'),
    # Rota para o mecânico aceitar a solicitação de manutenção
    path('aceitar-servico/<int:id>/', views.accept_maintenance, name='accept_maintenance'),
    # Rota para o mecânico concluir a manutenção
    path('concluir-servico/<int:id>/', views.finish_maintenance, name='finish_maintenance'),
    # Rota para o mecânico realizar a vistoria
    path('realizar-vistoria/<int:id>/', views.realizar_vistoria, name='realizar_vistoria'),
    # Rota para o cliente aprovar ou recusar a vistoria
    path('aprovar-vistoria/<int:id>/', views.aprovar_vistoria, name='aprovar_vistoria'),
    path('recusar-vistoria/<int:id>/', views.recusar_vistoria, name='recusar_vistoria'),
]