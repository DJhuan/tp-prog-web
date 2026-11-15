from django.contrib import admin
from django.utils.html import format_html

from .models import Produtora, Evento, TipoIngresso
from .filters import PeriodoEventoFilter, PrecoIngressoFilter, ProdutoraComEventosFilter


@admin.register(Produtora)
class ProdutoraAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "email", "telefone")
    search_fields = ("nome", "cnpj", "email")
    list_filter = (ProdutoraComEventosFilter, "data_cadastro")
    date_hierarchy = "data_cadastro"


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = (
        "miniatura",
        "nome",
        "data",
        "horario",
        "produtora",
        "coordenador",
        "status",
    )

    list_filter = (
        "status", PeriodoEventoFilter, "data",
        ("produtora", admin.RelatedOnlyFieldListFilter),
        ("coordenador", admin.RelatedOnlyFieldListFilter),
    )
    date_hierarchy = "data"
    list_select_related = ("produtora", "coordenador")
    search_fields = ("nome", "local")
    filter_horizontal = ("organizadores",)
    readonly_fields = ("previa_foto", "previa_banner")

    @staticmethod
    def _imagem(campo, altura):
        if not campo:
            return "—"
        return format_html(
            '<img src="{}" style="height:{}px;border-radius:4px;object-fit:cover;">',
            campo.url,
            altura,
        )

    @admin.display(description="Foto")
    def miniatura(self, obj):
        return self._imagem(obj.foto, 40)

    @admin.display(description="Prévia da foto")
    def previa_foto(self, obj):
        return self._imagem(obj.foto, 160)

    @admin.display(description="Prévia do banner")
    def previa_banner(self, obj):
        return self._imagem(obj.banner, 120)


@admin.register(TipoIngresso)
class TipoIngressoAdmin(admin.ModelAdmin):
    list_display = ("nome", "evento", "preco", "quantidade")
    list_filter = (
        ("evento", admin.RelatedOnlyFieldListFilter),
        ("evento__produtora", admin.RelatedOnlyFieldListFilter),
        PrecoIngressoFilter,
    )
    list_select_related = ("evento",)
    search_fields = ("nome", "evento__nome")
