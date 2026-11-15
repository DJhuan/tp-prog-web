from django.urls import path

from . import views

app_name = "ingressos"

urlpatterns = [
    path("carrinho/", views.carrinho_detalhe, name="carrinho"),
    path("carrinho/adicionar/<int:tipo_id>/", views.carrinho_adicionar, name="carrinho_adicionar"),
    path("carrinho/remover/<int:tipo_id>/", views.carrinho_remover, name="carrinho_remover"),
]
