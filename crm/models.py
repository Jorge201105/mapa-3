from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone

class Cliente(models.Model):
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    comuna = models.CharField(max_length=80, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.telefono or self.email or 'sin contacto'})"


class Producto(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=140)
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} [{self.sku}]"


class Venta(models.Model):
    class Canal(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        WHATSAPP = "whatsapp", "WhatsApp"
        WEB = "web", "Web"
        OTRO = "otro", "Otro"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas")
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.OTRO)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente.nombre} - {self.fecha.date()}"


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
