from django.urls import path
from .views import crear_cliente, cliente_creado



urlpatterns = [
    path("clientes/nuevo/", crear_cliente, name="crear_cliente"),
    path("clientes/ok/", cliente_creado, name="cliente_creado"),

]
