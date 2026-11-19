from django.urls import path

from . import views

app_name = "eventos"

urlpatterns = [
    path("", views.EventoListView.as_view(), name="lista"),
    path("eventos/<int:pk>/", views.EventoDetailView.as_view(), name="detalhe"),
    path("painel/eventos/", views.EventoGestaoListView.as_view(), name="gestao_lista"),
    path("painel/eventos/novo/", views.EventoCreateView.as_view(), name="gestao_criar"),
    path("painel/eventos/<int:pk>/editar/", views.EventoUpdateView.as_view(), name="gestao_editar"),
    path("painel/eventos/<int:pk>/excluir/", views.EventoDeleteView.as_view(), name="gestao_excluir"),
    path("painel/dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
