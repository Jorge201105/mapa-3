from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from django.db.models import Sum, Count, Max, Value, DecimalField
from django.db.models.functions import Coalesce

from .forms import ClienteForm
from .forms_ventas import VentaForm
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
    # -------- leer filtros desde querystring --------
    segmento = (request.GET.get("segmento") or "").strip()   # VIP/Frecuente/Dormido/Ocasional
    comuna = (request.GET.get("comuna") or "").strip()
    min_kilos = (request.GET.get("min_kilos") or "").strip()
    orden = (request.GET.get("orden") or "kilos_desc").strip()  # kilos_desc / kilos_asc / id

    # -------- queryset base con métricas --------
    clientes_qs = (
        Cliente.objects
        .annotate(
            # Coalesce para que los que no tienen ventas queden en 0 (no None)
            gasto_total=Coalesce(Sum("ventas__total"), Value(0), output_field=DecimalField()),
            compras=Count("ventas", distinct=True),
            ultima_compra=Max("ventas__fecha"),
        )
    )

    # -------- filtro por comuna --------
    if comuna:
        clientes_qs = clientes_qs.filter(comuna__iexact=comuna)

    # -------- filtro por mínimo kilos --------
    if min_kilos:
        try:
            clientes_qs = clientes_qs.filter(gasto_total__gte=float(min_kilos))
        except ValueError:
            pass

    # -------- filtro por segmento (property -> Python) --------
    # OJO: aquí convertimos a lista si hay filtro de segmento.
    if segmento:
        clientes = [c for c in clientes_qs if c.segmento == segmento]
    else:
        clientes = clientes_qs

    # -------- orden --------
    if isinstance(clientes, list):
        # ordenar lista (cuando filtraste por segmento)
        if orden == "kilos_asc":
            clientes.sort(key=lambda x: (x.gasto_total or 0, x.id))
        elif orden == "kilos_desc":
            clientes.sort(key=lambda x: (x.gasto_total or 0, x.id), reverse=True)
        else:
            clientes.sort(key=lambda x: x.id)
    else:
        # ordenar queryset (sin filtro por segmento)
        if orden == "kilos_asc":
            clientes = clientes.order_by("gasto_total", "id")
        elif orden == "kilos_desc":
            clientes = clientes.order_by("-gasto_total", "id")
        else:
            clientes = clientes.order_by("id")

    # -------- lista de comunas para el select --------
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
            "f": request.GET,  # para mantener seleccionado en el form
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
    ventas = Venta.objects.select_related("cliente").order_by("id")
    return render(request, "crm/ventas_list.html", {"ventas": ventas})


def venta_nueva(request):
    cliente_id = request.GET.get("cliente")  # <-- viene desde ?cliente=ID

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
