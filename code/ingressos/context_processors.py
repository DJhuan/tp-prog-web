def carrinho(request):
    """Quantidade de ingressos no carrinho, para o contador da navbar."""
    itens = request.session.get("carrinho", {}) if hasattr(request, "session") else {}
    return {"carrinho_quantidade": sum(itens.values())}
