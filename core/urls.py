from django.contrib.auth import views as auth
from django.urls import path
from . import views

urlpatterns = [
    path('entrar/', auth.LoginView.as_view(template_name='login.html'), name='login'),
    path('sair/', auth.LogoutView.as_view(), name='logout'),
    path('', views.menu, name='menu'),
    path('estoque/', views.listagem, name='estoque'),
    path('vendas/', views.listagem, {'venda': True}, name='vendas'),
    path('estoque/novo/', views.nova_pesagem, name='novo_estoque'),
    path('estoque/<int:pk>/classificar/', views.classificacao, name='classificar'),
    path('vendas/nova/', views.novo, name='nova_venda'),
    path('vendas/<int:pk>/relatorio/', views.relatorio_venda, name='relatorio_venda'),
    path('cooperados/', views.cooperados, name='cooperados'),
    path('cooperados/novo/', views.editar_cooperado, name='novo_cooperado'),
    path('cooperados/<int:pk>/editar/', views.editar_cooperado, name='editar_cooperado'),
    path('cooperados/<int:pk>/excluir/', views.excluir_cooperado, name='excluir_cooperado'),
    path('painel/', views.painel, name='painel'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('relatorios/visualizar/', views.visualizar_relatorio, name='visualizar_relatorio'),
]
