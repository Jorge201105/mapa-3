from django.utils import timezone
from django.db.models import Sum, Max, Count
from .models import Venta, Importacion
from decimal import Decimal

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


from decimal import Decimal
from .models import Importacion

def costo_promedio_kg():
    qs = Importacion.objects.filter(activo=True)

    total_kilos = qs.aggregate(
        s=models.Sum("kilos_restantes")
    )["s"] or Decimal("0")

    total_costo = qs.aggregate(
        s=models.Sum("kilos_restantes") * 0
    )

    total_valor = sum(
        (i.kilos_restantes * i.costo_por_kg for i in qs),
        Decimal("0")
    )

    if total_kilos == 0:
        return Decimal("0")

    return (total_valor / total_kilos).quantize(Decimal("0.01"))


from decimal import Decimal
from django.db.models import Sum
from .models import Importacion


def costo_promedio_kg():
    """
    Costo promedio ponderado por kg usando importaciones activas
    y kilos_restantes como "stock vigente".
    """
    qs = Importacion.objects.filter(activo=True)

    total_kilos = qs.aggregate(s=Sum("kilos_restantes"))["s"] or Decimal("0")
    if total_kilos <= 0:
        return Decimal("0.00")

    # valor total del stock = sum(kilos_restantes * costo_por_kg)
    valor_total = Decimal("0")
    for imp in qs:
        valor_total += (imp.kilos_restantes or Decimal("0")) * (imp.costo_por_kg or Decimal("0"))

    return (valor_total / total_kilos).quantize(Decimal("0.01"))


def costo_promedio_kg():
    """
    Costo promedio ponderado por kg según importaciones ACTIVAS.
    Retorna Decimal (sin IVA).
    """
    qs = Importacion.objects.filter(activo=True)

    agg = qs.aggregate(
        kilos=Sum("kilos_ingresados"),
        costo=Sum("costo_total"),
    )

    kilos = agg["kilos"] or Decimal("0")
    costo = agg["costo"] or Decimal("0")

    if kilos <= 0:
        return Decimal("0")

    return (costo / kilos).quantize(Decimal("0.01"))