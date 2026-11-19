from django.urls import path

from . import views

app_name = "ingressos"

urlpatterns = [
    path("carrinho/", views.carrinho_detalhe, name="carrinho"),
    path("carrinho/adicionar/<int:tipo_id>/", views.carrinho_adicionar, name="carrinho_adicionar"),
    path("carrinho/remover/<int:tipo_id>/", views.carrinho_remover, name="carrinho_remover"),
    path("carrinho/comprar/", views.CompraView.as_view(), name="comprar"),
    path("meus-ingressos/", views.MeusIngressosView.as_view(), name="meus_ingressos"),
    path("portaria/", views.VerificarIngressoView.as_view(), name="verificar_ingresso"),
    path("portaria/eventos/", views.EventosDoOrganizadorView.as_view(), name="eventos_organizador"),
    path("portaria/<int:evento_id>/", views.ListaPresencaView.as_view(), name="lista_presenca"),
]
