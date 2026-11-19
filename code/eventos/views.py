
from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Min, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from contas.mixins import PerfilRequeridoMixin
from contas.models import Usuario

from .forms import EventoForm, TipoIngressoFormSet
from .models import Evento, TipoIngresso
from ingressos.models import Ingresso, Pedido


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


class CoordenadorQuerysetMixin(PerfilRequeridoMixin):
    perfis_permitidos = (Usuario.Perfil.COORDENADOR,)

    def get_queryset(self):
        produtora_id = self.request.user.produtora_id
        if not produtora_id:
            return Evento.objects.none()
        return Evento.objects.filter(produtora_id=produtora_id).select_related("produtora", "coordenador")


class EventoGestaoListView(CoordenadorQuerysetMixin, ListView):
    template_name = "eventos/gestao_lista.html"
    context_object_name = "eventos"
    paginate_by = 10


class EventoCreateView(PerfilRequeridoMixin, CreateView):
    perfis_permitidos = (Usuario.Perfil.COORDENADOR,)
    model = Evento
    form_class = EventoForm
    template_name = "eventos/gestao_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.produtora_id:
            messages.error(request, "Seu perfil de coordenador ainda não está vinculado a uma produtora.")
            return HttpResponseRedirect(reverse("eventos:gestao_lista"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = TipoIngressoFormSet(self.request.POST, self.request.FILES)
        else:
            context["formset"] = TipoIngressoFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if not formset.is_valid():
            return self.render_to_response(context)
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.produtora = self.request.user.produtora
            self.object.coordenador = self.request.user
            self.object.save()
            form.save_m2m()
            formset.instance = self.object
            formset.save()
        messages.success(self.request, "Evento criado com sucesso.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("eventos:gestao_lista")


class EventoUpdateView(CoordenadorQuerysetMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/gestao_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formset"] = kwargs.get("formset") or (
            TipoIngressoFormSet(self.request.POST, self.request.FILES, instance=self.object)
            if self.request.POST else TipoIngressoFormSet(instance=self.object)
        )
        return context

    def form_valid(self, form):
        formset = TipoIngressoFormSet(self.request.POST, self.request.FILES, instance=self.object)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
        messages.success(self.request, "Evento atualizado com sucesso.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("eventos:gestao_lista")


class EventoDeleteView(CoordenadorQuerysetMixin, DeleteView):
    model = Evento
    template_name = "eventos/gestao_confirmar_exclusao.html"
    success_url = reverse_lazy("eventos:gestao_lista")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Não é possível excluir um evento que já possui ingressos emitidos.")
            return HttpResponseRedirect(self.success_url)
        messages.success(self.request, "Evento excluído com sucesso.")
        return response


class DashboardView(PerfilRequeridoMixin, TemplateView):
    perfis_permitidos = (Usuario.Perfil.COORDENADOR,)
    template_name = "eventos/dashboard.html"

    def get_queryset_eventos(self):
        if not self.request.user.produtora_id:
            return Evento.objects.none()
        return Evento.objects.filter(produtora_id=self.request.user.produtora_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        eventos = self.get_queryset_eventos()
        resumo = eventos.aggregate(total=Count("id"), capacidade=Sum("capacidade"))
        ingressos_vendidos = Ingresso.objects.filter(
            tipo_ingresso__evento__in=eventos,
            pedido__status=Pedido.Status.APROVADO,
        ).exclude(status=Ingresso.Status.CANCELADO)
        vendas = ingressos_vendidos.aggregate(
            vendidos=Count("id"),
            checkins=Count("id", filter=Q(status=Ingresso.Status.UTILIZADO)),
            receita=Sum("tipo_ingresso__preco"),
        )
        por_tipo = list(
            ingressos_vendidos.values("tipo_ingresso__nome")
            .annotate(total=Count("id"))
            .order_by("tipo_ingresso__nome")
        )
        por_dia = list(
            ingressos_vendidos.annotate(dia=TruncDate("pedido__data_compra"))
            .values("dia")
            .annotate(total=Count("id"))
            .order_by("dia")
        )
        capacidade = resumo["capacidade"] or 0
        vendidos = vendas["vendidos"] or 0
        checkins = vendas["checkins"] or 0
        context.update({
            "total_eventos": resumo["total"] or 0,
            "capacidade_total": capacidade,
            "ingressos_vendidos": vendidos,
            "receita": vendas["receita"] or 0,
            "checkins_feitos": checkins,
            "ocupacao_percentual": round(vendidos / capacidade * 100, 1) if capacidade else 0,
            "checkins_percentual": round(checkins / vendidos * 100, 1) if vendidos else 0,
            "vendas_tipo_json": [item["tipo_ingresso__nome"] for item in por_tipo],
            "vendas_tipo_valores_json": [item["total"] for item in por_tipo],
            "vendas_dia_json": [item["dia"].strftime("%d/%m/%Y") for item in por_dia],
            "vendas_dia_valores_json": [item["total"] for item in por_dia],
            "eventos": eventos.order_by("-data")[:8],
        })
        return context
