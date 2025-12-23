from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    comuna = models.CharField(max_length=80, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    observaciones = models.TextField(blank=True)  # 👈 NUEVO
    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def segmento(self):
        from .services import segmentar_cliente
        return segmentar_cliente(self)[0]

    @property
    def segmento_color(self):
        from .services import segmentar_cliente
        return segmentar_cliente(self)[1]

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

    # ✅ Nuevo: tipo de documento (Factura/Boleta)
    class TipoDocumento(models.TextChoices):
        SIN_DOC = "sin_doc", "Sin documento"
        BOLETA = "boleta", "Boleta"
        FACTURA = "factura", "Factura"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas")
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.OTRO)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)  # 👈 NUEVO
    

    # ✅ Nuevos campos
    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        default=TipoDocumento.SIN_DOC,
        db_index=True,
    )
    numero_documento = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="N° Factura / Boleta",
        db_index=True,
    )

    class Meta:
        # (Opcional recomendado) Evita repetir el mismo número para el mismo tipo
        # Nota: permite múltiples SIN_DOC con numero_documento vacío.
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_documento", "numero_documento"],
                name="uniq_tipo_numero_documento",
                condition=~models.Q(numero_documento=""),
            )
        ]

    def __str__(self):
        doc = (
            f"{self.get_tipo_documento_display()} {self.numero_documento}"
            if self.numero_documento
            else "Sin doc"
        )
        return f"Venta #{self.id} - {self.cliente.nombre} - {self.fecha.date()} - {doc}"


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
