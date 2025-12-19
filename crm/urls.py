from django.urls import path
from .views import crear_cliente, cliente_creado
from . import views

app_name = "crm"

urlpatterns = [
    path("clientes/nuevo/", views.crear_cliente, name="crear_cliente"),
    path("clientes/ok/", cliente_creado, name="cliente_creado"),
    path("clientes/", views.clientes_list, name="clientes_list"),
     path("clientes/<int:cliente_id>/editar/", views.editar_cliente, name="editar_cliente"),
    path("clientes/<int:cliente_id>/borrar/", views.borrar_cliente, name="borrar_cliente"),
    path("ventas/", views.ventas_list, name="ventas_list"),
    path("ventas/nueva/", views.venta_nueva, name="venta_nueva"),
    path("ventas/<int:venta_id>/editar/", views.venta_editar, name="venta_editar"),
    path("ventas/<int:venta_id>/borrar/", views.venta_borrar, name="venta_borrar"),
    path("clientes/buscar-telefono/", views.buscar_cliente_telefono, name="buscar_cliente_telefono"),
]
