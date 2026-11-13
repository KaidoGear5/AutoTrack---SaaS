from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.master_login, name='master_login'), # Rota para a tela de login do painel master
    path('api/saude/', views.api_saude_servidor, name='api_saude_servidor'), # Rota para a API de saúde do servidor, que retorna dados de CPU e RAM em JSON
    path('usuario/status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'), # Rota para alternar o status de um usuário (ativo/inativo) no painel master
    path('usuario/excluir/<int:user_id>/', views.delete_user, name='delete_user'), # Rota para excluir um usuário do sistema no painel master
    path('clientes/', views.master_clientes, name='master_clientes'), # Rota para a aba de clientes do painel master, que lista todos os clientes cadastrados
    path('saude/', views.master_saude, name='master_saude'), # Rota para a aba de saúde do sistema no painel master, que mostra informações sobre o uso de CPU e RAM
    path('manutencao/toggle/', views.toggle_manutencao, name='toggle_manutencao'), # Rota para alternar o modo de manutenção do sistema, ativando ou desativando a página de manutenção
    path('', views.master_dashboard, name='master_dashboard'), # Rota para a tela principal do painel master, que mostra estatísticas e informações do sistema
]