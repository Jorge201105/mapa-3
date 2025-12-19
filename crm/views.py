from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ClienteForm

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


from .models import Cliente

def clientes_list(request):
    clientes = Cliente.objects.all().order_by("id")
    return render(request, "crm/clientes_list.html", {"clientes": clientes})

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Venta
from .forms_ventas import VentaForm


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


from django.shortcuts import render
from .models import Cliente

def buscar_cliente_telefono(request):
    cliente = None
    buscado = False

    if request.method == "POST":
        telefono = (request.POST.get("telefono") or "").strip()
        buscado = True

        if telefono:
            # búsqueda exacta por el campo telefono
            cliente = Cliente.objects.filter(telefono=telefono).first()

    return render(
        request,
        "crm/buscar_telefono.html",
        {"cliente": cliente, "buscado": buscado},
    )
