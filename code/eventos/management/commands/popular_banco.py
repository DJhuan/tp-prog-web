"""Popula o banco com dados de demonstração para a apresentação.

Uso:
    python manage.py popular_banco            # cria os dados (banco vazio)
    python manage.py popular_banco --limpar   # apaga os dados atuais e recria

Todos os usuários criados usam a senha definida em SENHA_PADRAO.
"""

import io
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from contas.models import Usuario
from eventos.models import Evento, Produtora, TipoIngresso
from ingressos.models import Ingresso, Pedido

SENHA_PADRAO = "eventa123"

PRODUTORAS = [
    {
        "nome": "Aurora Produções",
        "cnpj": "12.345.678/0001-90",
        "descricao": "Shows, festivais e grandes experiências musicais.",
        "email": "contato@auroraproducoes.com.br",
        "telefone": "(31) 3333-1000",
        "coordenador": ("coordenador@eventa.com", "Camila", "Rocha"),
    },
    {
        "nome": "Horizonte Cultural",
        "cnpj": "98.765.432/0001-10",
        "descricao": "Teatro, palestras e eventos de tecnologia.",
        "email": "contato@horizontecultural.com.br",
        "telefone": "(31) 3333-2000",
        "coordenador": ("coordenador2@eventa.com", "Rafael", "Mendes"),
    },
]

ORGANIZADORES = [
    ("organizador@eventa.com", "Lucas", "Ferreira"),
    ("organizador2@eventa.com", "Beatriz", "Lima"),
    ("organizador3@eventa.com", "Thiago", "Alves"),
]

PARTICIPANTES = [
    ("participante@eventa.com", "Ana", "Souza"),
    ("joao.silva@email.com", "João", "Silva"),
    ("maria.oliveira@email.com", "Maria", "Oliveira"),
    ("pedro.santos@email.com", "Pedro", "Santos"),
    ("julia.costa@email.com", "Júlia", "Costa"),
    ("gabriel.pereira@email.com", "Gabriel", "Pereira"),
    ("larissa.martins@email.com", "Larissa", "Martins"),
    ("felipe.gomes@email.com", "Felipe", "Gomes"),
    ("isabela.ribeiro@email.com", "Isabela", "Ribeiro"),
    ("matheus.carvalho@email.com", "Matheus", "Carvalho"),
]

# dias: deslocamento em relação a hoje (negativo = passado).
# organizadores: índices em ORGANIZADORES.
# vender: fração aproximada de cada tipo de ingresso que será vendida.
EVENTOS = [
    {
        "nome": "Festival Neon Summer",
        "descricao": "Uma noite inteira de música eletrônica com DJs nacionais e internacionais, "
                     "pista ao ar livre e um show de luzes inesquecível.",
        "dias": 12, "horario": time(20, 0), "local": "Mineirão, Belo Horizonte - MG",
        "capacidade": 300, "status": Evento.Status.PUBLICADO, "produtora": 0,
        "organizadores": [0, 1], "cores": ("#7b2ff7", "#f107a3"), "vender": 0.55,
        "tipos": [("Pista", "Acesso à pista principal.", "120.00", 200),
                  ("VIP", "Área exclusiva com open bar.", "280.00", 70),
                  ("Camarote", "Vista privilegiada do palco.", "450.00", 30)],
    },
    {
        "nome": "Rock na Praça",
        "descricao": "As melhores bandas de rock da cena independente em um festival gratuito "
                     "para toda a família, com food trucks e feira de artesanato.",
        "dias": 0, "horario": time(18, 0), "local": "Praça da Estação, Belo Horizonte - MG",
        "capacidade": 150, "status": Evento.Status.PUBLICADO, "produtora": 0,
        "organizadores": [0], "cores": ("#ff512f", "#dd2476"), "vender": 0.7,
        "tipos": [("Inteira", "Ingresso padrão.", "60.00", 100),
                  ("Meia-entrada", "Estudantes e idosos, com comprovante.", "30.00", 50)],
    },
    {
        "nome": "Noite do Samba",
        "descricao": "Roda de samba com convidados especiais, feijoada e muita música boa.",
        "dias": 25, "horario": time(19, 30), "local": "Casa de Shows Lapa, Belo Horizonte - MG",
        "capacidade": 120, "status": Evento.Status.PUBLICADO, "produtora": 0,
        "organizadores": [1], "cores": ("#f7971e", "#ffd200"), "vender": 0.35,
        "tipos": [("Pista", "Acesso geral.", "80.00", 90),
                  ("Mesa (4 pessoas)", "Mesa reservada para quatro pessoas.", "300.00", 30)],
    },
    {
        "nome": "Jazz ao Pôr do Sol",
        "descricao": "Uma tarde de jazz instrumental à beira da lagoa.",
        "dias": 40, "horario": time(17, 0), "local": "Lagoa da Pampulha, Belo Horizonte - MG",
        "capacidade": 80, "status": Evento.Status.RASCUNHO, "produtora": 0,
        "organizadores": [], "cores": ("#1e3c72", "#2a5298"), "vender": 0,
        "tipos": [("Inteira", "Ingresso padrão.", "90.00", 80)],
    },
    {
        "nome": "Festival de Inverno 2026",
        "descricao": "Edição de inverno do festival, com shows acústicos e gastronomia.",
        "dias": -20, "horario": time(16, 0), "local": "Parque Municipal, Belo Horizonte - MG",
        "capacidade": 200, "status": Evento.Status.ENCERRADO, "produtora": 0,
        "organizadores": [0, 1], "cores": ("#2193b0", "#6dd5ed"), "vender": 0.8,
        "check_in": 0.85,
        "tipos": [("Inteira", "Ingresso padrão.", "70.00", 150),
                  ("Meia-entrada", "Estudantes e idosos, com comprovante.", "35.00", 50)],
    },
    {
        "nome": "Tech Summit BH",
        "descricao": "Palestras e workshops sobre inteligência artificial, desenvolvimento web "
                     "e carreira em tecnologia, com profissionais de grandes empresas.",
        "dias": 8, "horario": time(9, 0), "local": "Expominas, Belo Horizonte - MG",
        "capacidade": 250, "status": Evento.Status.PUBLICADO, "produtora": 1,
        "organizadores": [2], "cores": ("#00c6ff", "#0072ff"), "vender": 0.5,
        "tipos": [("Estudante", "Válido com carteirinha.", "50.00", 120),
                  ("Profissional", "Acesso a todas as palestras.", "150.00", 100),
                  ("Workshop + Palestras", "Inclui os workshops práticos.", "320.00", 30)],
    },
    {
        "nome": "Peça: O Auto da Compadecida",
        "descricao": "Montagem clássica do texto de Ariano Suassuna, com elenco local.",
        "dias": 18, "horario": time(20, 30), "local": "Teatro Sesiminas, Belo Horizonte - MG",
        "capacidade": 100, "status": Evento.Status.PUBLICADO, "produtora": 1,
        "organizadores": [2], "cores": ("#c31432", "#240b36"), "vender": 0.6,
        "tipos": [("Plateia", "Assentos da plateia.", "70.00", 70),
                  ("Balcão", "Assentos do balcão.", "45.00", 30)],
    },
    {
        "nome": "Stand-up: Rindo à Toa",
        "descricao": "Uma noite de comédia com quatro humoristas da nova geração.",
        "dias": 5, "horario": time(21, 0), "local": "Teatro Bradesco, Belo Horizonte - MG",
        "capacidade": 60, "status": Evento.Status.PUBLICADO, "produtora": 1,
        "organizadores": [1, 2], "cores": ("#11998e", "#38ef7d"), "vender": 0.95,
        "tipos": [("Inteira", "Ingresso padrão.", "60.00", 40),
                  ("Meia-entrada", "Estudantes e idosos, com comprovante.", "30.00", 20)],
    },
    {
        "nome": "Workshop de Fotografia",
        "descricao": "Workshop prático de fotografia urbana, cancelado por motivo de força maior.",
        "dias": 15, "horario": time(10, 0), "local": "Centro Cultural, Belo Horizonte - MG",
        "capacidade": 30, "status": Evento.Status.CANCELADO, "produtora": 1,
        "organizadores": [], "cores": ("#434343", "#000000"), "vender": 0,
        "tipos": [("Vaga", "Inclui material de apoio.", "180.00", 30)],
    },
]


class Command(BaseCommand):
    help = "Popula o banco com dados de demonstração para a apresentação."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Apaga eventos, pedidos, produtoras e usuários (exceto superusuários) antes de popular.",
        )
        parser.add_argument(
            "--sem-imagens",
            action="store_true",
            help="Não gera imagens de capa/banner para os eventos.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.rng = random.Random(42)  # mesmos dados a cada execução

        if options["limpar"]:
            self.limpar()
        elif Produtora.objects.exists() or Evento.objects.exists():
            raise CommandError(
                "O banco já tem dados. Use --limpar para apagar tudo e recriar."
            )

        self.criar_usuarios_base()
        produtoras = self.criar_produtoras()
        organizadores = [self.criar_usuario(*dados, Usuario.Perfil.ORGANIZADOR) for dados in ORGANIZADORES]
        participantes = [self.criar_usuario(*dados, Usuario.Perfil.PARTICIPANTE) for dados in PARTICIPANTES]

        for dados in EVENTOS:
            evento = self.criar_evento(dados, produtoras, organizadores, options["sem_imagens"])
            self.vender_ingressos(evento, dados, participantes)

        self.resumo()

    # ------------------------------------------------------------------ limpeza

    def limpar(self):
        # A ordem respeita os on_delete=PROTECT entre os modelos.
        Ingresso.objects.all().delete()
        Pedido.objects.all().delete()
        for evento in Evento.objects.all():
            evento.foto.delete(save=False)
            evento.banner.delete(save=False)
        Evento.objects.all().delete()  # TipoIngresso vai junto (CASCADE)
        Usuario.objects.filter(is_superuser=False).delete()
        Produtora.objects.all().delete()
        self.stdout.write(self.style.WARNING("Dados anteriores apagados."))

    # ----------------------------------------------------------------- usuários

    def criar_usuario(self, email, nome, sobrenome, perfil, **extra):
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            usuario = Usuario.objects.create_user(
                email=email, password=SENHA_PADRAO, first_name=nome,
                last_name=sobrenome, perfil=perfil, **extra,
            )
        return usuario

    def criar_usuarios_base(self):
        if not Usuario.objects.filter(email="admin@eventa.com").exists():
            Usuario.objects.create_superuser(
                email="admin@eventa.com", password=SENHA_PADRAO,
                first_name="Admin", last_name="Eventa",
            )

        # O vendedor entra no admin (is_staff) e cuida de produtoras e usuários.
        vendedor = self.criar_usuario(
            "vendedor@eventa.com", "Vitor", "Nunes", Usuario.Perfil.VENDEDOR, is_staff=True,
        )
        vendedor.user_permissions.set(Permission.objects.filter(
            content_type__app_label__in=["eventos", "contas"],
            content_type__model__in=["produtora", "usuario"],
            codename__regex=r"^(view|add|change)_",
        ))

    def criar_produtoras(self):
        produtoras = []
        for dados in PRODUTORAS:
            dados = dict(dados)
            coordenador = dados.pop("coordenador")
            produtora = Produtora.objects.create(**dados)
            self.criar_usuario(*coordenador, Usuario.Perfil.COORDENADOR, produtora=produtora)
            produtoras.append(produtora)
        return produtoras

    # ------------------------------------------------------------------ eventos

    def criar_evento(self, dados, produtoras, organizadores, sem_imagens):
        produtora = produtoras[dados["produtora"]]
        evento = Evento.objects.create(
            nome=dados["nome"],
            descricao=dados["descricao"],
            data=timezone.localdate() + timedelta(days=dados["dias"]),
            horario=dados["horario"],
            local=dados["local"],
            capacidade=dados["capacidade"],
            status=dados["status"],
            produtora=produtora,
            coordenador=produtora.coordenadores.first(),
        )
        evento.organizadores.set([organizadores[i] for i in dados["organizadores"]])

        for nome, descricao, preco, quantidade in dados["tipos"]:
            TipoIngresso.objects.create(
                evento=evento, nome=nome, descricao=descricao,
                preco=Decimal(preco), quantidade=quantidade,
            )

        if not sem_imagens:
            slug = f"evento-{evento.pk}"
            evento.foto.save(f"{slug}.png", gerar_imagem(dados["nome"], dados["cores"], (800, 600)), save=False)
            evento.banner.save(f"{slug}.png", gerar_imagem(dados["nome"], dados["cores"], (1600, 500)), save=False)
            evento.save(update_fields=["foto", "banner"])

        return evento

    def vender_ingressos(self, evento, dados, participantes):
        """Cria pedidos aprovados até atingir a fração de vendas definida."""
        if not dados["vender"]:
            return

        tipos = list(evento.tipos_ingresso.all())
        metas = {tipo.pk: int(tipo.quantidade * dados["vender"]) for tipo in tipos}
        vendidos = {tipo.pk: 0 for tipo in tipos}
        agora = timezone.now()
        # As compras acontecem nos 30 dias anteriores ao evento (ou a hoje, se for futuro).
        limite = min(agora, timezone.make_aware(datetime.combine(evento.data, evento.horario)))
        organizadores = list(evento.organizadores.all())
        taxa_check_in = dados.get("check_in", 0)

        while any(vendidos[pk] < metas[pk] for pk in metas):
            participante = self.rng.choice(participantes)
            disponiveis = [t for t in tipos if vendidos[t.pk] < metas[t.pk]]
            itens = []
            for tipo in self.rng.sample(disponiveis, k=min(len(disponiveis), self.rng.choice([1, 1, 2]))):
                quantidade = min(self.rng.randint(1, 4), metas[tipo.pk] - vendidos[tipo.pk])
                vendidos[tipo.pk] += quantidade
                itens.append((tipo, quantidade))

            pedido = Pedido.objects.create(
                participante=participante,
                status=Pedido.Status.APROVADO,
                valor_total=sum(tipo.preco * qtd for tipo, qtd in itens),
            )
            # data_compra usa auto_now_add, então é ajustada depois de criada.
            data_compra = limite - timedelta(days=self.rng.randint(0, 29), minutes=self.rng.randint(0, 1440))
            Pedido.objects.filter(pk=pedido.pk).update(data_compra=data_compra)

            for tipo, quantidade in itens:
                for _ in range(quantidade):
                    ingresso = Ingresso(pedido=pedido, tipo_ingresso=tipo)
                    if organizadores and self.rng.random() < taxa_check_in:
                        ingresso.status = Ingresso.Status.UTILIZADO
                        ingresso.organizador = self.rng.choice(organizadores)
                        ingresso.data_validacao = timezone.make_aware(
                            datetime.combine(evento.data, evento.horario)
                        ) + timedelta(minutes=self.rng.randint(-30, 90))
                    ingresso.save()

    # ------------------------------------------------------------------- resumo

    def resumo(self):
        self.stdout.write(self.style.SUCCESS("\nBanco populado com sucesso!\n"))
        self.stdout.write(
            f"  {Produtora.objects.count()} produtoras, {Evento.objects.count()} eventos, "
            f"{TipoIngresso.objects.count()} tipos de ingresso, {Pedido.objects.count()} pedidos, "
            f"{Ingresso.objects.count()} ingressos\n"
        )
        self.stdout.write(f"Logins de demonstração (senha: {SENHA_PADRAO}):")
        contas = [
            ("Administrador", "admin@eventa.com"),
            ("Vendedor", "vendedor@eventa.com"),
            ("Coordenador (Aurora)", "coordenador@eventa.com"),
            ("Coordenador (Horizonte)", "coordenador2@eventa.com"),
            ("Organizador", "organizador@eventa.com"),
            ("Participante", "participante@eventa.com"),
        ]
        for papel, email in contas:
            self.stdout.write(f"  {papel:<25} {email}")

        ingresso = Ingresso.objects.filter(
            status=Ingresso.Status.DISPONIVEL,
            tipo_ingresso__evento__data=timezone.localdate(),
        ).first()
        if ingresso:
            self.stdout.write(
                f"\nCódigo para testar o check-in hoje ({ingresso.tipo_ingresso.evento.nome}):\n"
                f"  {ingresso.codigo}"
            )


def gerar_imagem(titulo, cores, tamanho):
    """Gera uma imagem com degradê e o nome do evento, usada como capa/banner."""
    largura, altura = tamanho
    inicio = Image.new("RGB", tamanho, cores[0])
    fim = Image.new("RGB", tamanho, cores[1])
    vertical = Image.linear_gradient("L").resize(tamanho)
    horizontal = Image.linear_gradient("L").rotate(90).transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize(tamanho)
    mascara = Image.blend(horizontal, vertical, 0.5)  # degradê diagonal
    imagem = Image.composite(fim, inicio, mascara)

    desenho = ImageDraw.Draw(imagem)
    fonte = ImageFont.load_default(size=altura // 9)
    caixa = desenho.textbbox((0, 0), titulo, font=fonte)
    while caixa[2] - caixa[0] > largura * 0.9 and fonte.size > 12:
        fonte = ImageFont.load_default(size=fonte.size - 4)
        caixa = desenho.textbbox((0, 0), titulo, font=fonte)
    posicao = ((largura - (caixa[2] - caixa[0])) / 2, (altura - (caixa[3] - caixa[1])) / 2)
    desenho.text(posicao, titulo, font=fonte, fill="white", stroke_width=2, stroke_fill=(0, 0, 0, 80))

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue())
