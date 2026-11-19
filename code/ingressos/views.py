from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.views.generic import ListView, FormView, View
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from contas.models import Usuario
from contas.mixins import PerfilRequeridoMixin
from eventos.models import Evento, TipoIngresso
from eventos.views import eventos_disponiveis

from .carrinho import Carrinho
from .forms import VerificarIngressoForm
from .models import Ingresso, Pedido


def carrinho_detalhe(request):
    itens = list(Carrinho(request))
    return render(request, "ingressos/carrinho.html", {
        "itens": itens,
        "total": sum(item["subtotal"] for item in itens),
    })


@require_POST
def carrinho_adicionar(request, tipo_id):
    tipo = get_object_or_404(
        TipoIngresso.objects.select_related("evento"),
        pk=tipo_id,
        evento__in=eventos_disponiveis(),
    )

    try:
        quantidade = int(request.POST.get("quantidade", 1))
    except ValueError:
        quantidade = 0

    if quantidade < 1:
        messages.error(request, "Informe uma quantidade válida.")
        return redirect("eventos:detalhe", pk=tipo.evento.pk)

    Carrinho(request).adicionar(tipo, quantidade)
    messages.success(request, f"{quantidade}x {tipo.nome} adicionado ao carrinho.")
    return redirect("ingressos:carrinho")


@require_POST
def carrinho_remover(request, tipo_id):
    Carrinho(request).remover(tipo_id)
    messages.info(request, "Item removido do carrinho.")
    return redirect("ingressos:carrinho")


class CompraView(PerfilRequeridoMixin, View):
    perfis_permitidos = (Usuario.Perfil.PARTICIPANTE,)
    http_method_names = ["post", "options"]

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.info(self.request, "Entre na sua conta para finalizar a compra.")
            return redirect_to_login(reverse("ingressos:carrinho"))
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        carrinho = Carrinho(request)
        if not carrinho.itens:
            messages.error(request, "Seu carrinho esta vazio.")
            return redirect("ingressos:carrinho")

        with transaction.atomic():
            tipos = {
                str(tipo.pk): tipo
                for tipo in TipoIngresso.objects.select_for_update()
                .filter(pk__in=carrinho.itens.keys(), evento__in=eventos_disponiveis())
                .select_related("evento")
            }
            problemas = []
            for chave, quantidade in carrinho.itens.items():
                tipo = tipos.get(chave)
                if tipo is None:
                    problemas.append("Um dos ingressos nao esta mais a venda e foi removido do carrinho.")
                elif quantidade > tipo.restantes:
                    restantes = tipo.restantes
                    problemas.append(
                        f"{tipo.nome} ({tipo.evento.nome}): voce pediu {quantidade}, mas so restam {restantes}."
                        if restantes else f"{tipo.nome} ({tipo.evento.nome}) esta esgotado."
                    )

            if problemas:
                for chave in [c for c in carrinho.itens if c not in tipos]:
                    carrinho.remover(chave)
                for problema in problemas:
                    messages.error(request, problema)
                return redirect("ingressos:carrinho")

            pedido = Pedido.objects.create(
                participante=request.user,
                status=Pedido.Status.APROVADO,
                valor_total=sum(
                    tipos[chave].preco * quantidade for chave, quantidade in carrinho.itens.items()
                ),
            )
            Ingresso.objects.bulk_create(
                Ingresso(pedido=pedido, tipo_ingresso=tipos[chave])
                for chave, quantidade in carrinho.itens.items()
                for _ in range(quantidade)
            )

        carrinho.limpar()
        messages.success(request, f"Compra realizada! Pedido #{pedido.pk} confirmado.")
        return redirect("ingressos:meus_ingressos")

class MeusIngressosView(PerfilRequeridoMixin, ListView):
    perfis_permitidos = (Usuario.Perfil.PARTICIPANTE,)
    template_name = "ingressos/meus_ingressos.html"
    context_object_name = "pedidos"

    def get_queryset(self):
        return Pedido.objects.filter(participante=self.request.user).prefetch_related(
            Prefetch(
                "ingressos",
                queryset=Ingresso.objects.select_related("tipo_ingresso__evento").order_by("pk"),
            )
        ).order_by("-data_compra")


class EventoOrganizadorMixin(PerfilRequeridoMixin):
    perfis_permitidos = (Usuario.Perfil.ORGANIZADOR,)

    def get_evento(self):
        if not hasattr(self, "_evento"):
            self._evento = get_object_or_404(
                Evento.objects.filter(organizadores=self.request.user), pk=self.kwargs["evento_id"]
            )
        return self._evento


class EventosDoOrganizadorView(PerfilRequeridoMixin, ListView):
    perfis_permitidos = (Usuario.Perfil.ORGANIZADOR,)
    template_name = "ingressos/eventos_organizador.html"
    context_object_name = "eventos"

    def get_queryset(self):
        return Evento.objects.filter(organizadores=self.request.user).order_by("data", "horario")


class ListaPresencaView(EventoOrganizadorMixin, ListView):
    template_name = "ingressos/lista_presenca.html"
    context_object_name = "ingressos"
    paginate_by = 50

    def get_queryset(self):
        return Ingresso.objects.filter(
            tipo_ingresso__evento=self.get_evento(), pedido__status=Pedido.Status.APROVADO
        ).exclude(status=Ingresso.Status.CANCELADO).select_related(
            "pedido__participante", "tipo_ingresso"
        ).order_by("pedido__participante__first_name", "pedido__participante__email")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.get_evento()
        return context


class VerificarIngressoView(PerfilRequeridoMixin, FormView):
    perfis_permitidos = (Usuario.Perfil.ORGANIZADOR,)
    form_class = VerificarIngressoForm
    template_name = "ingressos/verificar_ingresso.html"

    def form_valid(self, form):
        with transaction.atomic():
            ingresso = Ingresso.objects.select_for_update().select_related(
                "pedido", "tipo_ingresso__evento", "organizador"
            ).filter(
                codigo=form.cleaned_data["codigo"],
                tipo_ingresso__evento__organizadores=self.request.user,
            ).first()
            if not ingresso:
                messages.error(self.request, "Ingresso nao encontrado em evento alocado a voce.")
            elif ingresso.pedido.status != Pedido.Status.APROVADO:
                messages.error(self.request, "Este ingresso nao possui uma compra aprovada.")
            elif ingresso.status == Ingresso.Status.CANCELADO:
                messages.error(self.request, "Este ingresso foi cancelado.")
            elif ingresso.status == Ingresso.Status.UTILIZADO:
                hora = timezone.localtime(ingresso.data_validacao).strftime("%d/%m/%Y as %H:%M") if ingresso.data_validacao else "em horario nao registrado"
                validador = (ingresso.organizador.get_full_name() or ingresso.organizador.email) if ingresso.organizador else "organizador nao identificado"
                messages.warning(self.request, f"Ingresso ja utilizado por {validador}, em {hora}.")
            elif ingresso.status != Ingresso.Status.DISPONIVEL:
                messages.error(self.request, "O status deste ingresso nao permite o check-in.")
            else:
                ingresso.status = Ingresso.Status.UTILIZADO
                ingresso.data_validacao = timezone.now()
                ingresso.organizador = self.request.user
                ingresso.save(update_fields=["status", "data_validacao", "organizador"])
                participante = ingresso.pedido.participante
                nome = participante.get_full_name() or participante.email
                evento = ingresso.tipo_ingresso.evento.nome
                messages.success(self.request, f"Check-in realizado para {nome} no evento {evento}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ingressos:verificar_ingresso")