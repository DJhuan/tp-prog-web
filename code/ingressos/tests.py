from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contas.models import Usuario
from eventos.models import Evento, Produtora, TipoIngresso
from .models import Ingresso, Pedido


class CarrinhoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        produtora = Produtora.objects.create(nome="Prod", cnpj="444", email="p@example.com")
        coord = Usuario.objects.create_user(email="c@example.com", perfil="COORDENADOR", produtora=produtora)

        def evento(status="PUBLICADO"):
            return Evento.objects.create(
                nome="Show", data=timezone.localdate() + timedelta(days=5), horario=time(20),
                local="Arena", capacidade=100, produtora=produtora, coordenador=coord, status=status,
            )

        cls.evento = evento()
        cls.pista = TipoIngresso.objects.create(nome="Pista", preco=50, quantidade=3, evento=cls.evento)
        cls.vip = TipoIngresso.objects.create(nome="VIP", preco="120.50", quantidade=10, evento=cls.evento)
        cls.rascunho = TipoIngresso.objects.create(
            nome="Oculto", preco=10, quantidade=10, evento=evento(status="RASCUNHO")
        )

    def adicionar(self, tipo, quantidade):
        return self.client.post(
            reverse("ingressos:carrinho_adicionar", args=[tipo.pk]), {"quantidade": quantidade}
        )

    def test_adicionar_soma_e_mostra_total(self):
        self.adicionar(self.pista, 1)
        self.adicionar(self.pista, 1)
        response = self.adicionar(self.vip, 2)
        self.assertRedirects(response, reverse("ingressos:carrinho"))
        self.assertEqual(self.client.session["carrinho"], {str(self.pista.pk): 2, str(self.vip.pk): 2})

        response = self.client.get(reverse("ingressos:carrinho"))
        self.assertEqual(response.context["total"], 341)
        self.assertContains(response, "R$ 341,00")
        self.assertContains(response, '<span class="badge text-bg-primary rounded-pill">4</span>', html=True)

    def test_quantidade_limitada_ao_estoque(self):
        participante = Usuario.objects.create_user(email="u@example.com", perfil="PARTICIPANTE")
        pedido = Pedido.objects.create(participante=participante, valor_total=50)
        Ingresso.objects.create(pedido=pedido, tipo_ingresso=self.pista)

        response = self.adicionar(self.pista, 5)
        self.assertEqual(self.client.session["carrinho"], {str(self.pista.pk): 2})
        self.assertContains(self.client.get(response.url), "Só restam 2")

    def test_esgotado_nao_entra_no_carrinho(self):
        participante = Usuario.objects.create_user(email="u@example.com", perfil="PARTICIPANTE")
        pedido = Pedido.objects.create(participante=participante, valor_total=150)
        for _ in range(3):
            Ingresso.objects.create(pedido=pedido, tipo_ingresso=self.pista)

        response = self.adicionar(self.pista, 1)
        self.assertRedirects(response, reverse("eventos:detalhe", args=[self.evento.pk]))
        self.assertEqual(self.client.session["carrinho"], {})

    def test_quantidade_invalida(self):
        for valor in ("0", "-2", "abc"):
            with self.subTest(valor=valor):
                self.adicionar(self.vip, valor)
                self.assertEqual(self.client.session.get("carrinho", {}), {})

    def test_evento_nao_publicado_da_404_e_get_nao_permitido(self):
        self.assertEqual(self.adicionar(self.rascunho, 1).status_code, 404)
        response = self.client.get(reverse("ingressos:carrinho_adicionar", args=[self.vip.pk]))
        self.assertEqual(response.status_code, 405)

    def test_remover(self):
        self.adicionar(self.pista, 1)
        self.adicionar(self.vip, 1)
        self.client.post(reverse("ingressos:carrinho_remover", args=[self.pista.pk]))
        self.assertEqual(self.client.session["carrinho"], {str(self.vip.pk): 1})

    def test_carrinho_vazio(self):
        self.assertContains(self.client.get(reverse("ingressos:carrinho")), "Seu carrinho está vazio")

    def test_detalhe_mostra_formulario_so_com_estoque(self):
        response = self.client.get(reverse("eventos:detalhe", args=[self.evento.pk]))
        self.assertContains(response, reverse("ingressos:carrinho_adicionar", args=[self.vip.pk]))
