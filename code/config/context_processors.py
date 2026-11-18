

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from eventos.models import Evento
from ingressos.models import Pedido, Ingresso


def eventa_dashboard(request):
    if request.path.rstrip("/") != "/admin":
        return {}

    hoje = timezone.localdate()
    periodo = request.GET.get("periodo", "30d")

    # Define o intervalo selecionado
    if periodo == "hoje":
        inicio = hoje
    elif periodo == "7d":
        inicio = hoje - timedelta(days=6)
    elif periodo == "30d":
        inicio = hoje - timedelta(days=29)
    elif periodo == "mes":
        inicio = hoje.replace(day=1)
    else:
        periodo = "todos"
        inicio = None

    pedidos = Pedido.objects.filter(status="APROVADO")
    eventos = Evento.objects.all()

    if inicio:
        pedidos = pedidos.filter(data_compra__date__gte=inicio)
        eventos = eventos.filter(data__gte=inicio)

    pedidos = pedidos.filter(data_compra__date__lte=hoje)
    eventos = eventos.filter(data__lte=hoje)

    # Pedidos por situação no período
    pedidos_periodo = Pedido.objects.all()

    if inicio:
        pedidos_periodo = pedidos_periodo.filter(
            data_compra__date__gte=inicio
        )

    pedidos_periodo = pedidos_periodo.filter(
        data_compra__date__lte=hoje
    )

    total_aprovados = pedidos_periodo.filter(
        status="APROVADO"
    ).count()

    total_pendentes = pedidos_periodo.filter(
        status="PENDENTE"
    ).count()

    total_cancelados = pedidos_periodo.filter(
        status="CANCELADO"
    ).count()

    total_pedidos_periodo = (
        total_aprovados + total_pendentes + total_cancelados
    )

    # Faturamento
    faturamento = pedidos.aggregate(
        total=Sum("valor_total")
    )["total"] or Decimal("0.00")

    # Ingressos vendidos: pedidos aprovados, sem ingressos cancelados
    ingressos_vendidos = Ingresso.objects.filter(
        pedido__status="APROVADO"
    ).exclude(
        status="CANCELADO"
    )

    if inicio:
        ingressos_vendidos = ingressos_vendidos.filter(
            pedido__data_compra__date__gte=inicio
        )

    ingressos_vendidos = ingressos_vendidos.filter(
        pedido__data_compra__date__lte=hoje
    )

    total_ingressos = ingressos_vendidos.count()

    total_utilizados = ingressos_vendidos.filter(
        status="UTILIZADO"
    ).count()

    total_disponiveis = ingressos_vendidos.filter(
        status="DISPONIVEL"
    ).count()

    # Eventos realizados e futuros
    eventos_realizados = Evento.objects.filter(
        status="ENCERRADO",
        data__lte=hoje
    )

    eventos_futuros = Evento.objects.filter(
        data__gt=hoje
    ).exclude(
        status="CANCELADO"
    )

    if inicio:
        eventos_realizados = eventos_realizados.filter(
            data__gte=inicio
        )

        eventos_futuros = eventos_futuros.filter(
            data__gte=inicio
        )

    total_eventos_realizados = eventos_realizados.count()

    # Vendas por dia
    # Para "todos", mostramos os últimos 30 dias no gráfico.
    inicio_grafico = inicio or (hoje - timedelta(days=29))

    vendas_por_dia = (
        pedidos
        .filter(data_compra__date__gte=inicio_grafico)
        .annotate(dia=TruncDate("data_compra"))
        .values("dia")
        .annotate(
            quantidade=Count(
                "ingressos",
                filter=~Q(ingressos__status="CANCELADO")
            )
        )
        .order_by("dia")
    )

    vendas_dict = {
        item["dia"]: item["quantidade"]
        for item in vendas_por_dia
    }

    quantidade_dias = (hoje - inicio_grafico).days + 1

    grafico_vendas = []

    for i in range(quantidade_dias):
        dia = inicio_grafico + timedelta(days=i)

        grafico_vendas.append({
            "dia": dia.strftime("%d/%m"),
            "quantidade": vendas_dict.get(dia, 0),
        })

    maior_venda_dia = max(
        [item["quantidade"] for item in grafico_vendas] or [0]
    )

    for item in grafico_vendas:
        item["altura"] = (
            round(item["quantidade"] / maior_venda_dia * 100)
            if maior_venda_dia else 0
        )

    # Ranking de eventos por ingressos vendidos
    ranking_eventos = (
        Ingresso.objects
        .filter(pedido__status="APROVADO")
        .exclude(status="CANCELADO")
    )

    if inicio:
        ranking_eventos = ranking_eventos.filter(
            pedido__data_compra__date__gte=inicio
        )

    ranking_eventos = (
        ranking_eventos
        .filter(pedido__data_compra__date__lte=hoje)
        .values(
            "tipo_ingresso__evento__id",
            "tipo_ingresso__evento__nome"
        )
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    maior_ranking = max(
        [item["total"] for item in ranking_eventos] or [0]
    )

    ranking = []

    for item in ranking_eventos:
        ranking.append({
            "nome": item["tipo_ingresso__evento__nome"],
            "total": item["total"],
            "percentual": (
                round(item["total"] / maior_ranking * 100)
                if maior_ranking else 0
            ),
        })

    # Percentuais dos gráficos de pizza
    def percentual(valor, total):
        return round(valor / total * 100) if total else 0

    return {
        "dashboard_periodo": periodo,

        "dashboard_faturamento": faturamento,
        "dashboard_total_ingressos": total_ingressos,
        "dashboard_ingressos_utilizados": total_utilizados,
        "dashboard_ingressos_disponiveis": total_disponiveis,

        "dashboard_eventos_realizados": total_eventos_realizados,
        "dashboard_eventos_futuros": eventos_futuros.count(),

        "dashboard_pedidos_aprovados": total_aprovados,
        "dashboard_pedidos_pendentes": total_pendentes,
        "dashboard_pedidos_cancelados": total_cancelados,

        "dashboard_aprovados_pct": percentual(
            total_aprovados, total_pedidos_periodo
        ),
        "dashboard_pendentes_pct": percentual(
            total_pendentes, total_pedidos_periodo
        ),
        "dashboard_cancelados_pct": percentual(
            total_cancelados, total_pedidos_periodo
        ),

        "dashboard_utilizados_pct": percentual(
            total_utilizados, total_ingressos
        ),
        "dashboard_disponiveis_pct": percentual(
            total_disponiveis, total_ingressos
        ),

        "dashboard_grafico_vendas": grafico_vendas,
        "dashboard_ranking_eventos": ranking,
    }

