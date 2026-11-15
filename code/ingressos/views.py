from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from contas.models import Usuario
from eventos.models import TipoIngresso
from eventos.views import eventos_disponiveis

from .carrinho import Carrinho
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


@require_POST
def comprar(request):
    if not request.user.is_authenticated:
        messages.info(request, "Entre na sua conta para finalizar a compra.")
        return redirect_to_login(reverse("ingressos:carrinho"))

    if request.user.perfil != Usuario.Perfil.PARTICIPANTE:
        messages.error(request, "Apenas participantes podem comprar ingressos.")
        return redirect("ingressos:carrinho")

    carrinho = Carrinho(request)
    if not carrinho.itens:
        messages.error(request, "Seu carrinho está vazio.")
        return redirect("ingressos:carrinho")

    with transaction.atomic():
        # Trava os tipos de ingresso para que duas compras simultâneas não
        # vendam o mesmo lugar (no PostgreSQL; o SQLite já serializa escritas).
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
                problemas.append("Um dos ingressos não está mais à venda e foi removido do carrinho.")
            elif quantidade > tipo.restantes:
                restantes = tipo.restantes
                problemas.append(
                    f"{tipo.nome} ({tipo.evento.nome}): você pediu {quantidade}, "
                    f"mas só restam {restantes}."
                    if restantes else f"{tipo.nome} ({tipo.evento.nome}) está esgotado."
                )

        if problemas:
            for chave in [c for c in carrinho.itens if c not in tipos]:
                carrinho.remover(chave)
            for problema in problemas:
                messages.error(request, problema)
            return redirect("ingressos:carrinho")

        pedido = Pedido.objects.create(
            participante=request.user,
            status=Pedido.Status.APROVADO,  # pagamento simulado
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


@login_required
def meus_ingressos(request):
    pedidos = (
        Pedido.objects.filter(participante=request.user)
        .prefetch_related(
            Prefetch(
                "ingressos",
                queryset=Ingresso.objects.select_related("tipo_ingresso__evento").order_by("pk"),
            )
        )
        .order_by("-data_compra")
    )
    return render(request, "ingressos/meus_ingressos.html", {"pedidos": pedidos})
