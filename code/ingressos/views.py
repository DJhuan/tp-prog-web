from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from eventos.models import TipoIngresso
from eventos.views import eventos_disponiveis

from .carrinho import Carrinho


def carrinho_detalhe(request):
    carrinho = Carrinho(request)
    itens = list(carrinho)
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

    carrinho = Carrinho(request)
    pedido = carrinho.itens.get(str(tipo.pk), 0) + quantidade
    final = carrinho.adicionar(tipo, quantidade)

    if final == 0:
        messages.error(request, f"{tipo.nome} está esgotado.")
        return redirect("eventos:detalhe", pk=tipo.evento.pk)
    if final < pedido:
        messages.warning(request, f"Só restam {final} ingressos de {tipo.nome}; o carrinho foi ajustado.")
    else:
        messages.success(request, f"{quantidade}x {tipo.nome} adicionado ao carrinho.")
    return redirect("ingressos:carrinho")


@require_POST
def carrinho_remover(request, tipo_id):
    Carrinho(request).remover(tipo_id)
    messages.info(request, "Item removido do carrinho.")
    return redirect("ingressos:carrinho")
