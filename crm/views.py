from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from django.db import models
from django.db.models import Sum, Count, Max, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth

from .forms import ClienteForm, VentaForm, VentaItemForm
from .models import Cliente, Venta, VentaItem


# -----------------
# CLIENTES
# -----------------
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


def clientes_list(request):
    segmento = (request.GET.get("segmento") or "").strip()
    comuna = (request.GET.get("comuna") or "").strip()
    min_kilos = (request.GET.get("min_kilos") or "").strip()
    orden = (request.GET.get("orden") or "kilos_desc").strip()

    dec_money = DecimalField(max_digits=12, decimal_places=2)
    dec_kilos = DecimalField(max_digits=12, decimal_places=2)

    clientes_qs = (
        Cliente.objects.annotate(
            kilos_acumulados=Coalesce(
                Sum("ventas__kilos_total"), Value(0), output_field=dec_kilos
            ),
            gasto_total=Coalesce(
                Sum("ventas__monto_total"), Value(0), output_field=dec_money
            ),
            compras=Count("ventas", distinct=True),
            ultima_compra=Max("ventas__fecha"),
        )
    )

    if comuna:
        clientes_qs = clientes_qs.filter(comuna__iexact=comuna)

    if min_kilos:
        try:
            clientes_qs = clientes_qs.filter(kilos_acumulados__gte=float(min_kilos))
        except ValueError:
            pass

    # filtro por segmento (tu segmento es @property)
    if segmento:
        clientes = [c for c in clientes_qs if c.segmento == segmento]
    else:
        clientes = clientes_qs

    # Orden
    if isinstance(clientes, list):
        if orden == "kilos_asc":
            clientes.sort(key=lambda x: (x.kilos_acumulados or 0, x.id))
        elif orden == "kilos_desc":
            clientes.sort(key=lambda x: (x.kilos_acumulados or 0, x.id), reverse=True)
        elif orden == "gasto_asc":
            clientes.sort(key=lambda x: (x.gasto_total or 0, x.id))
        elif orden == "gasto_desc":
            clientes.sort(key=lambda x: (x.gasto_total or 0, x.id), reverse=True)
        else:
            clientes.sort(key=lambda x: x.id)
    else:
        if orden == "kilos_asc":
            clientes = clientes.order_by("kilos_acumulados", "id")
        elif orden == "kilos_desc":
            clientes = clientes.order_by("-kilos_acumulados", "id")
        elif orden == "gasto_asc":
            clientes = clientes.order_by("gasto_total", "id")
        elif orden == "gasto_desc":
            clientes = clientes.order_by("-gasto_total", "id")
        else:
            clientes = clientes.order_by("id")

    comunas = (
        Cliente.objects.exclude(comuna="")
        .values_list("comuna", flat=True)
        .distinct()
        .order_by("comuna")
    )

    return render(
        request,
        "crm/clientes_list.html",
        {"clientes": clientes, "comunas": comunas, "f": request.GET},
    )


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
    nombre = cliente.nombre
    cliente.delete()
    messages.success(request, f"Cliente eliminado: {nombre}")
    return redirect("crm:clientes_list")


# -----------------
# VENTAS
# -----------------
def ventas_list(request):
    tipo_doc = (request.GET.get("tipo_documento") or "").strip()
    canal = (request.GET.get("canal") or "").strip()
    orden_id = (request.GET.get("orden_id") or "desc").strip()
    min_kilos = (request.GET.get("min_kilos") or "").strip()
    max_kilos = (request.GET.get("max_kilos") or "").strip()

    ventas = Venta.objects.select_related("cliente")

    if tipo_doc in ["boleta", "factura", "sin_doc", "nota_credito"]:
        ventas = ventas.filter(tipo_documento=tipo_doc)

    if canal:
        ventas = ventas.filter(canal=canal)

    if min_kilos:
        try:
            ventas = ventas.filter(kilos_total__gte=float(min_kilos))
        except ValueError:
            pass

    if max_kilos:
        try:
            ventas = ventas.filter(kilos_total__lte=float(max_kilos))
        except ValueError:
            pass

    ventas = ventas.order_by("id") if orden_id == "asc" else ventas.order_by("-id")

    return render(request, "crm/ventas_list.html", {"ventas": ventas, "f": request.GET})


def venta_nueva(request):
    """
    ✅ CAMBIO CLAVE:
    - Al guardar la venta, redirige al detalle (/crm/ventas/<id>/) para agregar ítems.
    - Si viene ?cliente=<id>, precarga el cliente.
    """
    cliente_id = request.GET.get("cliente")

    if request.method == "POST":
        form = VentaForm(request.POST)
        if form.is_valid():
            venta = form.save()
            messages.success(
                request, "Venta creada. Ahora agrega los ítems para calcular el total ($)."
            )
            return redirect("crm:venta_detalle", venta_id=venta.id)
    else:
        initial = {}
        if cliente_id:
            initial["cliente"] = cliente_id
        form = VentaForm(initial=initial)

    return render(request, "crm/venta_form.html", {"form": form, "modo": "crear"})


def venta_editar(request, venta_id):
    """
    ✅ CAMBIO:
    - Al guardar edición, vuelve al detalle para seguir agregando ítems.
    """
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == "POST":
        form = VentaForm(request.POST, instance=venta)
        if form.is_valid():
            venta = form.save()
            messages.success(request, "Venta actualizada correctamente.")
            return redirect("crm:venta_detalle", venta_id=venta.id)
    else:
        form = VentaForm(instance=venta)

    return render(
        request, "crm/venta_form.html", {"form": form, "modo": "editar", "venta": venta}
    )


@require_POST
def venta_borrar(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    venta.delete()
    messages.success(request, "Venta eliminada.")
    return redirect("crm:ventas_list")


# -----------------
# ✅ DETALLE + ÍTEMS
# -----------------
def venta_detalle(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    items = venta.items.select_related("producto").all().order_by("id")
    form_item = VentaItemForm()

    return render(
        request,
        "crm/venta_detalle.html",
        {"venta": venta, "items": items, "form_item": form_item},
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


# -----------------
# ✅ RESUMEN MENSUAL
# -----------------
def resumen_mensual(request):
    qs = (
        Venta.objects.annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(
            kilos=Coalesce(
                Sum("kilos_total"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            ventas_brutas=Coalesce(
                Sum("monto_total", filter=~models.Q(tipo_documento="nota_credito")),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            notas_credito=Coalesce(
                Sum("monto_total", filter=models.Q(tipo_documento="nota_credito")),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            cantidad_ventas=Count("id"),
        )
        .order_by("-mes")
    )

    filas = []
    for r in qs:
        ventas_brutas = r["ventas_brutas"] or Decimal("0")
        notas = r["notas_credito"] or Decimal("0")
        filas.append(
            {
                "mes": r["mes"],
                "kilos": r["kilos"] or Decimal("0"),
                "ventas_brutas": ventas_brutas,
                "notas_credito": notas,
                "neto": ventas_brutas - notas,
                "cantidad_ventas": r["cantidad_ventas"],
            }
        )

    total_kilos = sum((f["kilos"] for f in filas), Decimal("0"))
    total_bruto = sum((f["ventas_brutas"] for f in filas), Decimal("0"))
    total_notas = sum((f["notas_credito"] for f in filas), Decimal("0"))
    total_neto = total_bruto - total_notas

    return render(
        request,
        "crm/resumen_mensual.html",
        {
            "filas": filas,
            "totales": {
                "kilos": total_kilos,
                "ventas_brutas": total_bruto,
                "notas_credito": total_notas,
                "neto": total_neto,
            },
        },
    )


# -----------------
# BUSCADORES
# -----------------
def buscar_cliente_telefono(request):
    cliente = None
    buscado = False

    if request.method == "POST":
        telefono = (request.POST.get("telefono") or "").strip()
        buscado = True
        if telefono:
            cliente = Cliente.objects.filter(telefono=telefono).first()

    return render(
        request, "crm/buscar_telefono.html", {"cliente": cliente, "buscado": buscado}
    )


def buscar_cliente_por_nombre(request):
    cliente = None
    query = ""

    if request.method == "POST":
        query = request.POST.get("nombre", "").strip()
        if query:
            cliente = Cliente.objects.filter(nombre__icontains=query).first()

    return render(
        request,
        "crm/buscar_cliente_nombre.html",
        {"cliente": cliente, "query": query},
    )
