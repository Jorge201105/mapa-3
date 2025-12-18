from django.contrib import admin
from django.db.models import Sum, Count, Max
from .models import Cliente, Venta, VentaItem
from .services import segmentar_cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "telefono",
        "email",
        "get_gasto_total",
        "get_compras",
        "get_ultima_compra",
        "get_segmento",
    )

    list_filter = ("comuna",)
    search_fields = ("nombre", "telefono", "email")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            gasto_total=Sum("ventas__total"),
            compras=Count("ventas"),
            ultima_compra=Max("ventas__fecha"),
        )

    def get_gasto_total(self, obj):
        return obj.gasto_total or 0
    get_gasto_total.short_description = "Gasto total"
    get_gasto_total.admin_order_field = "gasto_total"

    def get_compras(self, obj):
        return obj.compras
    get_compras.short_description = "N° compras"
    get_compras.admin_order_field = "compras"

    def get_ultima_compra(self, obj):
        return obj.ultima_compra
    get_ultima_compra.short_description = "Última compra"

    def get_segmento(self, obj):
        return segmentar_cliente(obj)
    get_segmento.short_description = "Segmento"


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha", "total", "canal")
    list_filter = ("canal", "fecha")
    date_hierarchy = "fecha"


@admin.register(VentaItem)
class VentaItemAdmin(admin.ModelAdmin):
    list_display = ("venta", "producto", "cantidad", "precio_unitario")


