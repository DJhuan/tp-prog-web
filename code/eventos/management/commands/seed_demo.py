from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from eventos.models import Evento, Produtora, TipoIngresso
from ingressos.models import Ingresso, Pedido


class Command(BaseCommand):
    help = "Cria dados fictícios de demonstração para o EVENTA."

    password = "EventaDemo2026!"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando só pode ser executado com DEBUG=True, em ambiente de desenvolvimento.")

        User = get_user_model()
        hoje = timezone.localdate()

        produtoras = {}
        for slug, nome, cnpj, email in [
            ("aurora", "Aurora Produções", "12.345.678/0001-90", "contato@auroraproducoes.example"),
            ("horizonte", "Horizonte Cultural", "98.765.432/0001-10", "contato@horizontecultural.example"),
        ]:
            produtoras[slug], _ = Produtora.objects.update_or_create(
                cnpj=cnpj,
                defaults={
                    "nome": nome,
                    "descricao": "Produtora fictícia criada para demonstração do EVENTA.",
                    "email": email,
                    "telefone": "(35) 3000-0000",
                },
            )

        usuarios = {}
        definicoes = [
            ("admin.demo@eventa.example", "Ana", "Administradora", "ADMINISTRADOR", None, True),
            ("vendedor.demo@eventa.example", "Bruno", "Vendedor", "VENDEDOR", None, False),
            ("coordenador.aurora@eventa.example", "Camila", "Coordenadora", "COORDENADOR", "aurora", False),
            ("coordenador.horizonte@eventa.example", "Diego", "Coordenador", "COORDENADOR", "horizonte", False),
            ("organizador.1@eventa.example", "Elisa", "Organizadora", "ORGANIZADOR", None, False),
            ("organizador.2@eventa.example", "Felipe", "Organizador", "ORGANIZADOR", None, False),
        ]
        for email, primeiro_nome, sobrenome, perfil, produtora_slug, staff in definicoes:
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": primeiro_nome,
                    "last_name": sobrenome,
                    "perfil": perfil,
                    "produtora": produtoras.get(produtora_slug),
                    "is_active": True,
                    "is_staff": staff,
                    "is_superuser": perfil == "ADMINISTRADOR",
                },
            )
            user.set_password(self.password)
            user.save(update_fields=["password"])
            usuarios[email] = user

        participantes = []
        for n in range(1, 7):
            email = f"participante{n:02d}@eventa.example"
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": ["Marina", "Lucas", "Sofia", "Rafael", "Beatriz", "Caio"][n - 1],
                    "last_name": "Participante Demo",
                    "perfil": "PARTICIPANTE",
                    "produtora": None,
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            user.set_password(self.password)
            user.save(update_fields=["password"])
            participantes.append(user)

        eventos = []
        definicoes_eventos = [
            {
                "slug": "tecnologia",
                "nome": "Encontro de Tecnologia e Inovação",
                "dias": 14,
                "hora": time(9, 0),
                "local": "Centro de Convenções de Lavras",
                "capacidade": 120,
                "status": Evento.Status.PUBLICADO,
                "produtora": "aurora",
                "coordenador": "coordenador.aurora@eventa.example",
                "precos": [("Lote promocional", "35.00", 40), ("Inteira", "60.00", 80)],
            },
            {
                "slug": "cultura",
                "nome": "Festival Cultura em Movimento",
                "dias": 30,
                "hora": time(18, 30),
                "local": "Praça Dr. Augusto Silva, Lavras",
                "capacidade": 250,
                "status": Evento.Status.PUBLICADO,
                "produtora": "horizonte",
                "coordenador": "coordenador.horizonte@eventa.example",
                "precos": [("Entrada social", "20.00", 100), ("Inteira", "40.00", 150)],
            },
            {
                "slug": "acessibilidade",
                "nome": "Oficina de Acessibilidade Digital",
                "dias": 45,
                "hora": time(14, 0),
                "local": "Auditório do Campus Universitário",
                "capacidade": 60,
                "status": Evento.Status.PUBLICADO,
                "produtora": "aurora",
                "coordenador": "coordenador.aurora@eventa.example",
                "precos": [("Participação", "15.00", 60)],
            },
            {
                "slug": "rascunho",
                "nome": "Mostra de Projetos Universitários",
                "dias": 60,
                "hora": time(10, 0),
                "local": "Pavilhão de Eventos, Lavras",
                "capacidade": 90,
                "status": Evento.Status.RASCUNHO,
                "produtora": "horizonte",
                "coordenador": "coordenador.horizonte@eventa.example",
                "precos": [("Entrada", "10.00", 90)],
            },
        ]

        for spec in definicoes_eventos:
            evento, _ = Evento.objects.update_or_create(
                nome=spec["nome"],
                defaults={
                    "descricao": f"Evento demonstrativo fictício do projeto EVENTA: {spec['nome']}.",
                    "data": hoje + timedelta(days=spec["dias"]),
                    "horario": spec["hora"],
                    "local": spec["local"],
                    "capacidade": spec["capacidade"],
                    "status": spec["status"],
                    "produtora": produtoras[spec["produtora"]],
                    "coordenador": usuarios[spec["coordenador"]],
                },
            )
            eventos.append((evento, spec))
            if spec["slug"] != "rascunho":
                evento.organizadores.set([usuarios["organizador.1@eventa.example"], usuarios["organizador.2@eventa.example"]])
            else:
                evento.organizadores.clear()

            for nome_tipo, preco, quantidade in spec["precos"]:
                TipoIngresso.objects.update_or_create(
                    evento=evento,
                    nome=nome_tipo,
                    defaults={
                        "descricao": "Ingresso fictício para demonstração.",
                        "preco": Decimal(preco),
                        "quantidade": quantidade,
                    },
                )

        # Pedidos aprovados e check-ins dão conteúdo à carteira, lista de presença e dashboard.
        for evento, spec in eventos[:3]:
            tipo = evento.tipos_ingresso.order_by("preco").first()
            for indice, participante in enumerate(participantes[:4]):
                pedido = (
                    Pedido.objects.filter(
                        participante=participante,
                        status=Pedido.Status.APROVADO,
                        ingressos__tipo_ingresso=tipo,
                    )
                    .distinct()
                    .first()
                )
                if pedido is None:
                    pedido = Pedido.objects.create(
                        participante=participante,
                        status=Pedido.Status.APROVADO,
                        valor_total=tipo.preco,
                    )
                    # Permite que os gráficos mostrem vendas em dias diferentes.
                    Pedido.objects.filter(pk=pedido.pk).update(
                        data_compra=timezone.now() - timedelta(days=indice + 1)
                    )
                ingresso, _ = Ingresso.objects.get_or_create(pedido=pedido, tipo_ingresso=tipo)
                if indice == 0 and spec["slug"] == "tecnologia":
                    ingresso.status = Ingresso.Status.UTILIZADO
                    ingresso.organizador = usuarios["organizador.1@eventa.example"]
                    ingresso.data_validacao = timezone.now() - timedelta(hours=1)
                    ingresso.save(update_fields=["status", "organizador", "data_validacao"])

        self.stdout.write(self.style.SUCCESS(
            "Dados de demonstração criados/atualizados: 2 produtoras, 12 usuários, 4 eventos, tipos de ingresso e vendas."
        ))
        self.stdout.write(f"Senha comum das contas demo: {self.password}")
