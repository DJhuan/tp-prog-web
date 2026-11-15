from decimal import Decimal

from eventos.models import TipoIngresso


class Carrinho:
    CHAVE = "carrinho"

    def __init__(self, request):
        self.session = request.session
        self.itens = self.session.setdefault(self.CHAVE, {})

    def adicionar(self, tipo, quantidade):
        chave = str(tipo.pk)
        self.itens[chave] = self.itens.get(chave, 0) + quantidade
        self._salvar()

    def remover(self, tipo_id):
        self.itens.pop(str(tipo_id), None)
        self._salvar()

    def limpar(self):
        self.itens.clear()
        self._salvar()

    def _salvar(self):
        self.session.modified = True

    def __iter__(self):
        tipos = TipoIngresso.objects.filter(pk__in=self.itens.keys()).select_related("evento")
        for tipo in tipos:
            quantidade = self.itens[str(tipo.pk)]
            yield {
                "tipo": tipo,
                "quantidade": quantidade,
                "subtotal": tipo.preco * quantidade,
            }

    def __len__(self):
        return sum(self.itens.values())

    @property
    def total(self):
        return sum((item["subtotal"] for item in self), Decimal("0"))
