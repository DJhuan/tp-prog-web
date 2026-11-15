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

    def test_adicionar_nao_limita_ao_estoque(self):
        self.adicionar(self.pista, 5)
        self.assertEqual(self.client.session["carrinho"], {str(self.pista.pk): 5})

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


class CompraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        produtora = Produtora.objects.create(nome="Prod", cnpj="555", email="p@example.com")
        cls.coord = Usuario.objects.create_user(
            email="c@example.com", password="senha-123", perfil="COORDENADOR", produtora=produtora
        )
        cls.evento = Evento.objects.create(
            nome="Show", data=timezone.localdate() + timedelta(days=5), horario=time(20),
            local="Arena", capacidade=100, produtora=produtora, coordenador=cls.coord, status="PUBLICADO",
        )
        cls.pista = TipoIngresso.objects.create(nome="Pista", preco=50, quantidade=3, evento=cls.evento)
        cls.vip = TipoIngresso.objects.create(nome="VIP", preco=200, quantidade=10, evento=cls.evento)
        cls.participante = Usuario.objects.create_user(
            email="u@example.com", password="senha-123", perfil="PARTICIPANTE"
        )

    def encher_carrinho(self, itens):
        for tipo, quantidade in itens:
            self.client.post(
                reverse("ingressos:carrinho_adicionar", args=[tipo.pk]), {"quantidade": quantidade}
            )

    def comprar(self):
        return self.client.post(reverse("ingressos:comprar"))

    def test_compra_cria_pedido_e_ingressos_e_esvazia_carrinho(self):
        self.client.force_login(self.participante)
        self.encher_carrinho([(self.pista, 2), (self.vip, 1)])
        response = self.comprar()
        self.assertRedirects(response, reverse("ingressos:meus_ingressos"))

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.participante, self.participante)
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.valor_total, 300)
        self.assertEqual(pedido.ingressos.filter(tipo_ingresso=self.pista).count(), 2)
        self.assertEqual(pedido.ingressos.filter(tipo_ingresso=self.vip).count(), 1)
        self.assertEqual(len({i.codigo for i in pedido.ingressos.all()}), 3)
        self.assertEqual(self.client.session["carrinho"], {})

        response = self.client.get(response.url)
        self.assertContains(response, f"Pedido #{pedido.pk}")
        self.assertContains(response, str(pedido.ingressos.first().codigo))

    def test_quantidade_acima_do_estoque_bloqueia_a_compra_inteira(self):
        outro = Usuario.objects.create_user(email="o@example.com", perfil="PARTICIPANTE")
        anterior = Pedido.objects.create(participante=outro, valor_total=50)
        Ingresso.objects.create(pedido=anterior, tipo_ingresso=self.pista)

        self.client.force_login(self.participante)
        self.encher_carrinho([(self.pista, 3), (self.vip, 1)])
        response = self.comprar()
        self.assertRedirects(response, reverse("ingressos:carrinho"), fetch_redirect_response=False)
        self.assertEqual(Pedido.objects.filter(participante=self.participante).count(), 0)
        self.assertContains(self.client.get(response.url), "você pediu 3, mas só restam 2")
        self.assertEqual(len(self.client.session["carrinho"]), 2)

    def test_evento_despublicado_remove_item(self):
        self.client.force_login(self.participante)
        self.encher_carrinho([(self.pista, 1)])
        Evento.objects.filter(pk=self.evento.pk).update(status="CANCELADO")
        self.comprar()
        self.assertFalse(Pedido.objects.exists())
        self.assertEqual(self.client.session["carrinho"], {})

    def test_visitante_vai_para_login_e_carrinho_continua(self):
        self.encher_carrinho([(self.vip, 2)])
        response = self.comprar()
        self.assertRedirects(
            response, f"{reverse('contas:entrar')}?next={reverse('ingressos:carrinho')}",
            fetch_redirect_response=False,
        )
        self.client.post(response.url, {"username": "u@example.com", "password": "senha-123"})
        self.assertEqual(self.client.session["carrinho"], {str(self.vip.pk): 2})
        self.comprar()
        self.assertEqual(Pedido.objects.get().ingressos.count(), 2)

    def test_so_participante_compra(self):
        self.client.force_login(self.coord)
        self.encher_carrinho([(self.vip, 1)])
        self.comprar()
        self.assertFalse(Pedido.objects.exists())

    def test_carrinho_vazio_nao_cria_pedido(self):
        self.client.force_login(self.participante)
        self.comprar()
        self.assertFalse(Pedido.objects.exists())

    def test_meus_ingressos_mostra_so_os_do_usuario(self):
        outro = Usuario.objects.create_user(email="o@example.com", perfil="PARTICIPANTE")
        alheio = Pedido.objects.create(participante=outro, valor_total=50)
        Ingresso.objects.create(pedido=alheio, tipo_ingresso=self.pista)
        self.client.force_login(self.participante)
        response = self.client.get(reverse("ingressos:meus_ingressos"))
        self.assertEqual(list(response.context["pedidos"]), [])
        self.assertContains(response, "Você ainda não comprou ingressos")

    def test_meus_ingressos_exige_login(self):
        response = self.client.get(reverse("ingressos:meus_ingressos"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("contas:entrar"), response.url)
