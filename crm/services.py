from datetime import timedelta
from django.utils import timezone

def segmentar_cliente(c):
    hoy = timezone.now()
    dias = (hoy - (c.ultima_compra or c.creado_en)).days
    gasto = c.gasto_total or 0
    freq = c.compras or 0

    if freq >= 6 and gasto >= 300000 and dias <= 45:
        return "VIP"
    if freq >= 4 and dias <= 60:
        return "Frecuente"
    if dias > 120:
        return "Dormido"
    return "Ocasional"
