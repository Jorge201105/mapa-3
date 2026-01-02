
# crm/views.py
from decimal import Decimal
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum, Count, Max, Value, DecimalField, Q, DateField,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .models import Cliente, Venta, VentaItem, Producto, Importacion, GastoOperacional
from .forms import ClienteForm, VentaForm, VentaItemForm

from .services_inventario import consumo_bolsas



# crm/views.py

import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from django.db.models import (
    Sum, Count, Max, Q, F, Value,
    DecimalField, ExpressionWrapper
)
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from .forms import ClienteForm, VentaForm, VentaItemForm
from .models import Cliente, Venta, VentaItem, Producto, Importacion, GastoOperacional


# -------------------------
# Helpers
# -------------------------
def mes_key(value):
    """
    Normaliza cualquier fecha/datetime al primer día del mes (date)
    para que las llaves calcen entre Venta.fecha (DateTimeField)
    y GastoOperacional.fecha (DateField).
    """
    if value is None:
        return None
    if hasattr(value, "date"):
        value = value.date()
    return value.replace(day=1)


# -------------------------
# CLIENTES
# -------------------------
def clientes_list(request):
    segmento = request.GET.get("segmento", "").strip()
    comuna = request.GET.get("comuna", "").strip()
    min_kilos = request.GET.get("min_kilos", "").strip()
    orden = request.GET.get("orden", "").strip()

    qs = (
        Cliente.objects.all()
        .annotate(
            kilos_acumulados=Coalesce(
                Sum("ventas__kilos_total"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            gasto_total=Coalesce(
                Sum("ventas__monto_total"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            ultima=Max("ventas__fecha"),
            freq=Coalesce(
                Count("ventas"),
                Value(0),
            ),
        )
    )

    if comuna:
        qs = qs.filter(comuna=comuna)

    if min_kilos:
        try:
            mk = Decimal(min_kilos)
            qs = qs.filter(kilos_acumulados__gte=mk)
        except Exception:
            pass

    # Orden
    if orden == "kilos_asc":
        qs = qs.order_by("kilos_acumulados", "id")
    elif orden == "gasto_desc":
        qs = qs.order_by("-gasto_total", "-id")
    elif orden == "gasto_asc":
        qs = qs.order_by("gasto_total", "id")
    elif orden == "id":
        qs = qs.order_by("id")
    else:
        qs = qs.order_by("-kilos_acumulados", "-id")

    clientes = list(qs)

    # Segmento (si lo calculas en @property o service, filtra en Python)
    if segmento:
        clientes = [c for c in clientes if getattr(c, "segmento", "") == segmento]

    comunas = (
        Cliente.objects.exclude(comuna="")
        .values_list("comuna", flat=True)
        .distinct()
        .order_by("comuna")
    )

    context = {
        "clientes": clientes,
        "comunas": comunas,
        "f": {
            "segmento": segmento,
            "comuna": comuna,
            "min_kilos": min_kilos,
            "orden": orden,
        },
    }
    return render(request, "crm/clientes_list.html", context)



def crear_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente creado correctamente.")
            return redirect("crm:clientes_list")
    else:
        form = ClienteForm()
    return render(request, "crm/cliente_form.html", {"form": form, "modo": "crear"})


def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect("crm:clientes_list")
    else:
        form = ClienteForm(instance=cliente)

    return render(
        request,
        "crm/cliente_form.html",
        {"form": form, "modo": "editar", "cliente": cliente},
    )


@require_POST
def borrar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    cliente.delete()
    messages.success(request, "Cliente borrado correctamente.")
    return redirect("crm:clientes_list")


# -------------------------
# VENTAS
# -------------------------
def ventas_list(request):
    orden_id = request.GET.get("orden_id", "desc")
    tipo_documento = request.GET.get("tipo_documento", "").strip()
    canal = request.GET.get("canal", "").strip()
    min_kilos = request.GET.get("min_kilos", "").strip()
    max_kilos = request.GET.get("max_kilos", "").strip()

    qs = Venta.objects.select_related("cliente").all()

    if tipo_documento:
        qs = qs.filter(tipo_documento=tipo_documento)

    if canal:
        qs = qs.filter(canal=canal)

    if min_kilos:
        try:
            qs = qs.filter(kilos_total__gte=Decimal(min_kilos))
        except Exception:
            pass

    if max_kilos:
        try:
            qs = qs.filter(kilos_total__lte=Decimal(max_kilos))
        except Exception:
            pass

    if orden_id == "asc":
        qs = qs.order_by("id")
    else:
        qs = qs.order_by("-id")

    context = {
        "ventas": qs,
        "f": {
            "orden_id": orden_id,
            "tipo_documento": tipo_documento,
            "canal": canal,
            "min_kilos": min_kilos,
            "max_kilos": max_kilos,
        },
    }
    return render(request, "crm/ventas_list.html", context)


def venta_nueva(request):
    # Preselección desde buscadores: /crm/ventas/nueva/?cliente=ID
    cliente_id = request.GET.get("cliente")
    initial = {}
    if cliente_id:
        try:
            initial["cliente"] = Cliente.objects.get(id=int(cliente_id))
        except Exception:
            pass

    if request.method == "POST":
        form = VentaForm(request.POST)
        if form.is_valid():
            venta = form.save()
            messages.success(request, "Venta creada. Ahora agrega ítems.")
            # ✅ flujo natural: después de crear, ir a detalle para ingresar ítems
            return redirect("crm:venta_detalle", venta_id=venta.id)
    else:
        form = VentaForm(initial=initial)

    return render(request, "crm/venta_form.html", {"form": form, "modo": "crear"})


def venta_editar(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == "POST":
        form = VentaForm(request.POST, instance=venta)
        if form.is_valid():
            form.save()
            messages.success(request, "Venta actualizada correctamente.")
            return redirect("crm:venta_detalle", venta_id=venta.id)
    else:
        form = VentaForm(instance=venta)

    return render(
        request,
        "crm/venta_form.html",
        {"form": form, "modo": "editar", "venta": venta},
    )


@require_POST
def venta_borrar(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    venta.delete()
    messages.success(request, "Venta borrada.")
    return redirect("crm:ventas_list")


# -----------------
# VENTA DETALLE + ITEMS
# -----------------
def venta_detalle(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    items = venta.items.select_related("producto").all().order_by("id")
    form_item = VentaItemForm()

    # Para poblar tu <select> manual en template (productos)
    productos = Producto.objects.filter(activo=True).order_by("nombre")

    return render(
        request,
        "crm/venta_detalle.html",
        {"venta": venta, "items": items, "form_item": form_item, "productos": productos},
    )


@require_POST
def venta_item_agregar(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    form = VentaItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.venta = venta
        item.save()
        messages.success(request, "Ítem agregado.")
    else:
        messages.error(request, "No se pudo agregar el ítem. Revisa los campos.")
    return redirect("crm:venta_detalle", venta_id=venta.id)


@require_POST
def venta_item_borrar(request, item_id):
    item = get_object_or_404(VentaItem, id=item_id)
    venta_id = item.venta_id
    item.delete()
    messages.success(request, "Ítem eliminado.")
    return redirect("crm:venta_detalle", venta_id=venta_id)
# -------------------------
# BUSCADORES
# -------------------------
def buscar_cliente_telefono(request):
    cliente = None
    buscado = False

    if request.method == "POST":
        telefono = (request.POST.get("telefono") or "").strip()
        buscado = True
        if telefono:
            cliente = Cliente.objects.filter(telefono=telefono).first()

    return render(
        request,
        "crm/buscar_telefono.html",
        {"cliente": cliente, "buscado": buscado},
    )


def buscar_cliente_por_nombre(request):
    cliente = None
    query = ""

    if request.method == "POST":
        query = (request.POST.get("nombre") or "").strip()
        if query:
            cliente = (
                Cliente.objects.filter(nombre__icontains=query)
                .order_by("id")
                .first()
            )

    return render(
        request,
        "crm/buscar_cliente_nombre.html",
        {"cliente": cliente, "query": query},
    )


# -------------------------
# DASHBOARD (KPIs + gráficos)
# -------------------------
def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    desde = inicio_mes - timezone.timedelta(days=180)  # ~6 meses

    ventas = Venta.objects.filter(fecha__date__gte=desde)
    ventas_normales = ventas.exclude(tipo_documento=Venta.TipoDocumento.NOTA_CREDITO)

    ingresos = ventas_normales.aggregate(s=Sum("monto_total"))["s"] or Decimal("0")
    kilos = ventas.aggregate(s=Sum("kilos_total"))["s"] or Decimal("0")
    n_ventas = ventas_normales.count()

    ticket_prom = Decimal("0")
    if n_ventas > 0:
        ticket_prom = (ingresos / Decimal(n_ventas)).quantize(Decimal("1"))

    # --- Serie mensual ---
    serie_qs = (
        ventas.annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(
            ventas=Count("id"),
            kilos=Sum("kilos_total"),
            ingresos=Sum(
                "monto_total",
                filter=~Q(tipo_documento=Venta.TipoDocumento.NOTA_CREDITO),
            ),
        )
        .order_by("mes")
    )

    labels_mes, ingresos_mes, kilos_mes, ventas_mes = [], [], [], []
    for r in serie_qs:
        m = r["mes"]
        labels_mes.append(m.strftime("%m-%Y") if m else "")
        ingresos_mes.append(float(r["ingresos"] or 0))
        kilos_mes.append(float(r["kilos"] or 0))
        ventas_mes.append(int(r["ventas"] or 0))

    # --- Por canal ---
    por_canal_qs = (
        ventas.values("canal")
        .annotate(
            ventas=Count("id"),
            ingresos=Sum(
                "monto_total",
                filter=~Q(tipo_documento=Venta.TipoDocumento.NOTA_CREDITO),
            ),
        )
        .order_by("-ingresos")
    )
    canal_labels = [c["canal"] for c in por_canal_qs]
    canal_ingresos = [float(c["ingresos"] or 0) for c in por_canal_qs]

    # --- Top productos (KILOS por SKU) ---
    kilos_expr = ExpressionWrapper(
        F("cantidad") * F("producto__peso_kg"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    top_productos_qs = (
        VentaItem.objects
        .filter(venta__fecha__date__gte=desde)
        .exclude(venta__tipo_documento=Venta.TipoDocumento.NOTA_CREDITO)
        .values("producto__nombre")
        .annotate(kilos=Sum(kilos_expr))
        .order_by("-kilos")[:10]
    )

    prod_labels = [p["producto__nombre"] for p in top_productos_qs]
    prod_kilos = [float(p["kilos"] or 0) for p in top_productos_qs]

    context = {
        "desde": desde,
        "hoy": hoy,
        "kpi_ingresos": ingresos,
        "kpi_kilos": kilos,
        "kpi_n_ventas": n_ventas,
        "kpi_ticket": ticket_prom,

        # tablas
        "serie": list(serie_qs),
        "por_canal": list(por_canal_qs),
        "top_productos": list(top_productos_qs),

        # charts JSON
        "labels_mes_json": json.dumps(labels_mes),
        "ingresos_mes_json": json.dumps(ingresos_mes),
        "kilos_mes_json": json.dumps(kilos_mes),
        "ventas_mes_json": json.dumps(ventas_mes),

        "canal_labels_json": json.dumps(canal_labels),
        "canal_ingresos_json": json.dumps(canal_ingresos),

        "prod_labels_json": json.dumps(prod_labels),
        "prod_kilos_json": json.dumps(prod_kilos),
    }
    return render(request, "crm/dashboard.html", context)


# -------------------------
# RESUMEN MENSUAL (con costos + gastos + utilidad)
# -------------------------
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from django.db.models import Sum, Count, Value, DecimalField, Q
from django.db.models.functions import Coalesce, TruncMonth, ExtractYear, ExtractMonth

from .models import Venta, GastoOperacional, Importacion


# RESUMEN MENSUAL (ventas + costo + gastos + utilidad)
# -------------------------
def resumen_mensual(request):
    hoy = timezone.localdate()

    # Defaults: últimos 6 meses (desde inicio del mes actual hacia atrás)
    inicio_mes = hoy.replace(day=1)
    default_desde = inicio_mes - timedelta(days=180)
    default_hasta = hoy

    # GET filtros
    desde_str = (request.GET.get("desde") or "").strip()
    hasta_str = (request.GET.get("hasta") or "").strip()

    desde = parse_date(desde_str) if desde_str else default_desde
    hasta = parse_date(hasta_str) if hasta_str else default_hasta

    if not desde:
        desde = default_desde
    if not hasta:
        hasta = default_hasta
    if desde > hasta:
        desde, hasta = hasta, desde

    # Importación activa -> costo prom/kg
    imp_activa = Importacion.objects.filter(activo=True).order_by("-fecha").first()
    costo_por_kg = imp_activa.costo_por_kg if imp_activa else Decimal("0")

    # --------
    # VENTAS por mes (mes como DateField para evitar desfase por timezone)
    # --------
    ventas_qs = (
        Venta.objects
        .filter(fecha__date__gte=desde, fecha__date__lte=hasta)
        .annotate(mes=TruncMonth("fecha", output_field=DateField()))
        .values("mes")
        .annotate(
            kilos=Coalesce(
                Sum("kilos_total"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            ventas_brutas=Coalesce(
                Sum("monto_total", filter=~Q(tipo_documento=Venta.TipoDocumento.NOTA_CREDITO)),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            notas_credito=Coalesce(
                Sum("monto_total", filter=Q(tipo_documento=Venta.TipoDocumento.NOTA_CREDITO)),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            cantidad_ventas=Count("id"),
        )
        .order_by("-mes")
    )

    # --------
    # GASTOS por mes (mes como DateField)
    # --------
    gastos_qs = (
        GastoOperacional.objects
        .filter(fecha__gte=desde, fecha__lte=hasta)
        .annotate(mes=TruncMonth("fecha", output_field=DateField()))
        .values("mes")
        .annotate(
            gastos=Coalesce(
                Sum("monto_neto"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    )

    # Map: mes(date) -> gastos
    gastos_map = {r["mes"]: (r["gastos"] or Decimal("0")) for r in gastos_qs}

    filas = []
    for r in ventas_qs:
        mes = r["mes"]  # date (1er día del mes)
        kilos = r["kilos"] or Decimal("0")
        bruto = r["ventas_brutas"] or Decimal("0")
        notas = r["notas_credito"] or Decimal("0")

        ventas_netas = bruto - notas
        neto_real = ventas_netas  # por ahora igual (si luego sacas IVA, lo ajustas aquí)

        costo = (kilos * (costo_por_kg or Decimal("0"))).quantize(Decimal("0.01"))
        margen_bruto = neto_real - costo

        gastos = gastos_map.get(mes, Decimal("0"))
        utilidad = margen_bruto - gastos

        filas.append({
            "mes": mes,
            "kilos": kilos,
            "ventas_brutas": bruto,
            "notas_credito": notas,
            "ventas_netas": ventas_netas,
            "neto": neto_real,
            "cantidad_ventas": r["cantidad_ventas"],
            "costo": costo,
            "margen_bruto": margen_bruto,
            "gastos": gastos,
            "utilidad": utilidad,
        })

    totales = {
        "kilos": sum((f["kilos"] for f in filas), Decimal("0")),
        "ventas_brutas": sum((f["ventas_brutas"] for f in filas), Decimal("0")),
        "notas_credito": sum((f["notas_credito"] for f in filas), Decimal("0")),
        "ventas_netas": sum((f["ventas_netas"] for f in filas), Decimal("0")),
        "neto": sum((f["neto"] for f in filas), Decimal("0")),
        "costo": sum((f["costo"] for f in filas), Decimal("0")),
        "margen_bruto": sum((f["margen_bruto"] for f in filas), Decimal("0")),
        "gastos": sum((f["gastos"] for f in filas), Decimal("0")),
        "utilidad": sum((f["utilidad"] for f in filas), Decimal("0")),
    }

    return render(
        request,
        "crm/resumen_mensual.html",
        {
            "filas": filas,
            "totales": totales,
            "desde": desde,
            "hasta": hasta,
            "hoy": hoy,
            "costo_por_kg": costo_por_kg,
        },
    )



from decimal import Decimal
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce

from .models import Importacion, VentaItem, Venta


def inventario(request):
    """
    Inventario MVP por KILOS (sin bolsas):
    - Stock total (kg) = kilos_ingresados - kilos_vendidos
    - Kilos vendidos se calcula desde VentaItem: cantidad * producto.peso_kg
      excluyendo ventas con tipo_documento = NOTA_CREDITO
    - Consumo promedio diario en ventana configurable (default: 30 días)
    """

    hoy = timezone.localdate()

    # Ventana para consumo promedio (default 30 días)
    try:
        dias = int(request.GET.get("dias", "30"))
        if dias <= 0:
            dias = 30
    except Exception:
        dias = 30

    desde_consumo = hoy - timezone.timedelta(days=dias)

    # 1) Kilos ingresados (total)
    kilos_ingresados = (
        Importacion.objects.aggregate(
            s=Coalesce(
                Sum("kilos_ingresados"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["s"]
        or Decimal("0")
    )

    # 2) Kilos vendidos (desde items)
    kilos_expr = ExpressionWrapper(
        F("cantidad") * F("producto__peso_kg"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    kilos_vendidos_total = (
        VentaItem.objects.exclude(venta__tipo_documento=Venta.TipoDocumento.NOTA_CREDITO)
        .aggregate(
            s=Coalesce(
                Sum(kilos_expr),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["s"]
        or Decimal("0")
    )

    # 3) Stock actual (kg)
    stock_kg = (kilos_ingresados - kilos_vendidos_total).quantize(Decimal("0.01"))

    # 4) Consumo en ventana (kg vendidos últimos N días)
    kilos_vendidos_ventana = (
        VentaItem.objects.filter(venta__fecha__date__gte=desde_consumo)
        .exclude(venta__tipo_documento=Venta.TipoDocumento.NOTA_CREDITO)
        .aggregate(
            s=Coalesce(
                Sum(kilos_expr),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["s"]
        or Decimal("0")
    )

    # consumo diario (evitar división por 0)
    consumo_diario = Decimal("0.00")
    if dias > 0:
        consumo_diario = (kilos_vendidos_ventana / Decimal(dias)).quantize(Decimal("0.01"))

    # 5) Días de stock
    dias_stock = None
    fecha_reorden_estimada = None
    if consumo_diario > 0:
        dias_stock = (stock_kg / consumo_diario).quantize(Decimal("0.1"))
        fecha_reorden_estimada = hoy + timezone.timedelta(days=float(dias_stock))

    # 6) Umbral simple de alerta (puedes cambiarlo)
    umbral_reorden_dias = 14
    alerta_reorden = (dias_stock is not None) and (dias_stock <= Decimal(str(umbral_reorden_dias)))

    context = {
        "hoy": hoy,
        "dias": dias,
        "desde_consumo": desde_consumo,
        "kilos_ingresados": kilos_ingresados,
        "kilos_vendidos_total": kilos_vendidos_total,
        "stock_kg": stock_kg,
        "kilos_vendidos_ventana": kilos_vendidos_ventana,
        "consumo_diario": consumo_diario,
        "dias_stock": dias_stock,
        "fecha_reorden_estimada": fecha_reorden_estimada,
        "umbral_reorden_dias": umbral_reorden_dias,
        "alerta_reorden": alerta_reorden,
    }
    return render(request, "crm/inventario.html", context)
 

