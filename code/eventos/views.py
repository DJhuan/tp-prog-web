from django.db.models import Count, Min, Q
from django.utils import timezone
from django.views.generic import DetailView, ListView

from .models import Evento


def eventos_disponiveis():
    """Eventos publicados com data de hoje em diante."""
    return Evento.objects.filter(
        status=Evento.Status.PUBLICADO,
        data__gte=timezone.localdate(),
    ).select_related("produtora")


class EventoListView(ListView):
    template_name = "eventos/lista.html"
    context_object_name = "eventos"
    paginate_by = 9

    def get_queryset(self):
        eventos = eventos_disponiveis().annotate(
            preco_minimo=Min("tipos_ingresso__preco")
        )

        busca = self.request.GET.get("q", "").strip()
        if busca:
            eventos = eventos.filter(Q(nome__icontains=busca) | Q(local__icontains=busca))

        data_inicio = self.request.GET.get("data")
        if data_inicio:
            eventos = eventos.filter(data__gte=data_inicio)

        return eventos.order_by("data", "horario")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["busca"] = self.request.GET.get("q", "")
        contexto["data_filtro"] = self.request.GET.get("data", "")
        return contexto


class EventoDetailView(DetailView):
    template_name = "eventos/detalhe.html"
    context_object_name = "evento"

    def get_queryset(self):
        return eventos_disponiveis()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        tipos = self.object.tipos_ingresso.annotate(
            emitidos=Count("ingressos", filter=~Q(ingressos__status="CANCELADO"))
        ).order_by("preco")
        for tipo in tipos:
            tipo.disponiveis = max(tipo.quantidade - tipo.emitidos, 0)
        contexto["tipos_ingresso"] = tipos
        return contexto
