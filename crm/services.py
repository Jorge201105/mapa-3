from django.utils import timezone
from django.db.models import Sum, Max, Count
from .models import Venta


def segmentar_cliente(c):
    hoy = timezone.now()

    qs = Venta.objects.filter(cliente=c)

    agg = qs.aggregate(
        ultima=Max("fecha"),
        freq=Count("id"),
        kilos=Sum("kilos_total"),  # ✅ antes era "total"
    )

    ultima_compra = agg["ultima"] or c.creado_en
    dias = (hoy - ultima_compra).days
    freq = agg["freq"] or 0
    kilos = agg["kilos"] or 0  # ✅ kilos acumulados

    # 🔴 Dormido = red flag
    if freq > 0 and dias > 90:
        return "Dormido", "red"

    # 🟨 VIP
    if dias <= 45 and freq >= 2 and kilos >= 30:
        return "VIP", "gold"

    # 🟦 Frecuente
    if dias <= 60 and freq >= 1 and kilos >= 20:
        return "Frecuente", "blue"

    # ⚪ Ocasional
    return "Ocasional", "gray"
