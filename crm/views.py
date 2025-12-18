from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from .models import Cliente

def crear_cliente(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        telefono = request.POST.get("telefono")
        email = request.POST.get("email", "")
        comuna = request.POST.get("comuna", "")
        direccion = request.POST.get("direccion", "")

        # Evitar duplicados por teléfono si viene informado
        if telefono:
            Cliente.objects.get_or_create(
                telefono=telefono,
                defaults={
                    "nombre": nombre,
                    "email": email,
                    "comuna": comuna,
                    "direccion": direccion,
                }
            )
        else:
            Cliente.objects.create(
                nombre=nombre,
                email=email,
                comuna=comuna,
                direccion=direccion,
            )

        return redirect("cliente_creado")

    return render(request, "crm/crear_cliente.html")


def cliente_creado(request):
    return render(request, "crm/cliente_creado.html")
