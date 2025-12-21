from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from django.db.models import Sum, Count, Max, Value, DecimalField
from django.db.models.functions import Coalesce

# ✅ IMPORTS CORRECTOS: VentaForm sale de forms.py (el que incluye tipo_documento y numero_documento)
from .forms import ClienteForm, VentaForm

from .models import Cliente, Venta


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


def cliente_creado(request):
    return render(request, "crm/cliente_creado.html")


def clientes_list(request):
    segmento = (request.GET.get("segmento") or "").strip()
    comuna = (request.GET.get("comuna") or "").strip()
    min_kilos = (request.GET.get("min_kilos") or "").strip()
    orden = (request.GET.get("orden") or "kilos_desc").strip()

    clientes_qs = (
        Cliente.objects
        .annotate(
            gasto_total=Coalesce(Sum("ventas__total"), Value(0), output_field=DecimalField()),
            compras=Count("ventas", distinct=True),
            ultima_compra=Max("ventas__fecha"),
        )
    )

    if comuna:
        clientes_qs = clientes_qs.filter(comuna__iexact=comuna)

    if min_kilos:
        try:
            clientes_qs = clientes_qs.filter(gasto_total__gte=float(min_kilos))
        except ValueError:
            pass

    if segmento:
        clientes = [c for c in clientes_qs if c.segmento == segmento]
    else:
        clientes = clientes_qs

    if isinstance(clientes, list):
        if orden == "kilos_asc":
            clientes.sort(key=lambda x: (x.gasto_total or 0, x.id))
        elif orden == "kilos_desc":
            clientes.sort(key=lambda x: (x.gasto_total or 0, x.id), reverse=True)
        else:
            clientes.sort(key=lambda x: x.id)
    else:
        if orden == "kilos_asc":
            clientes = clientes.order_by("gasto_total", "id")
        elif orden == "kilos_desc":
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
        {
            "clientes": clientes,
            "comunas": comunas,
            "f": request.GET,
        },
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

    return render(request, "crm/cliente_form.html", {"form": form, "modo": "editar", "cliente": cliente})


@require_POST
def borrar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    nombre = cliente.nombre
    cliente.delete()
    messages.success(request, f"Cliente eliminado: {nombre}")
    return redirect("crm:clientes_list")


def ventas_list(request):
    tipo_doc = (request.GET.get("tipo_documento") or "").strip()
    canal = (request.GET.get("canal") or "").strip()
    orden_id = (request.GET.get("orden_id") or "desc").strip()  # asc | desc
    min_kilos = (request.GET.get("min_kilos") or "").strip()
    max_kilos = (request.GET.get("max_kilos") or "").strip()

    ventas = Venta.objects.select_related("cliente")

    # 🔎 Filtro por tipo de documento
    if tipo_doc in ["boleta", "factura", "sin_doc"]:
        ventas = ventas.filter(tipo_documento=tipo_doc)

    # 🔎 Filtro por canal
    if canal:
        ventas = ventas.filter(canal=canal)

    # 🔎 Filtro por kilos
    if min_kilos:
        try:
            ventas = ventas.filter(total__gte=float(min_kilos))
        except ValueError:
            pass

    if max_kilos:
        try:
            ventas = ventas.filter(total__lte=float(max_kilos))
        except ValueError:
            pass

    # ⬆️⬇️ Orden por ID
    if orden_id == "asc":
        ventas = ventas.order_by("id")
    else:
        ventas = ventas.order_by("-id")

    return render(
        request,
        "crm/ventas_list.html",
        {
            "ventas": ventas,
            "f": request.GET,
        },
    )





def venta_nueva(request):
    cliente_id = request.GET.get("cliente")  # viene desde ?cliente=ID

    if request.method == "POST":
        form = VentaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Venta creada correctamente.")
            return redirect("crm:ventas_list")
    else:
        initial = {}
        if cliente_id:
            initial["cliente"] = cliente_id
        form = VentaForm(initial=initial)

    return render(request, "crm/venta_form.html", {"form": form, "modo": "crear"})


def venta_editar(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == "POST":
        form = VentaForm(request.POST, instance=venta)
        if form.is_valid():
            form.save()
            messages.success(request, "Venta actualizada correctamente.")
            return redirect("crm:ventas_list")
    else:
        form = VentaForm(instance=venta)

    return render(request, "crm/venta_form.html", {"form": form, "modo": "editar", "venta": venta})


@require_POST
def venta_borrar(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    venta.delete()
    messages.success(request, "Venta eliminada.")
    return redirect("crm:ventas_list")


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
        query = request.POST.get("nombre", "").strip()
        if query:
            cliente = Cliente.objects.filter(nombre__icontains=query).first()

    return render(request, "crm/buscar_cliente_nombre.html", {
        "cliente": cliente,
        "query": query
    })
