from django.utils import timezone
from django.db.models import Sum, Max, Count
from .models import Venta

def segmentar_cliente(c):
    hoy = timezone.now()

    qs = Venta.objects.filter(cliente=c)

    agg = qs.aggregate(
        ultima=Max("fecha"),
        freq=Count("id"),
        kilos=Sum("total"),  # usa "total" como kilos (interno)
    )

    ultima_compra = agg["ultima"] or c.creado_en
    dias = (hoy - ultima_compra).days
    freq = agg["freq"] or 0
    gasto = agg["kilos"] or 0  # kilos

    # 🔴 Dormido = red flag
    if freq > 0 and dias > 90:
        return "Dormido", "red"

    # 🟨 VIP = amarillo (o verde si prefieres)
    if dias <= 45 and freq >= 2 and gasto >= 30:
        return "VIP", "gold"

    # 🟦 Frecuente = azul (o verde)
    if dias <= 60 and freq >= 1 and gasto >= 20:
        return "Frecuente", "blue"

    # ⚪ Ocasional = gris
    return "Ocasional", "gray"
