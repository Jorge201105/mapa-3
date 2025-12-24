from decimal import Decimal

from django.db import models
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.utils import timezone


class Cliente(models.Model):
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    comuna = models.CharField(max_length=80, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    observaciones = models.TextField(blank=True)
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

    precio_sugerido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio sugerido de venta (opcional)."
    )

    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} [{self.sku}]"


class Venta(models.Model):
    class Canal(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        WHATSAPP = "whatsapp", "WhatsApp"
        WEB = "web", "Web"
        OTRO = "otro", "Otro"

    class TipoDocumento(models.TextChoices):
        SIN_DOC = "sin_doc", "Sin documento"
        BOLETA = "boleta", "Boleta"
        FACTURA = "factura", "Factura"
        NOTA_CREDITO = "nota_credito", "Nota crédito"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas")
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.OTRO)

    # ⚖️ kilos ingresados manualmente (histórico / rápido)
    kilos_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # 💰 monto CON IVA (desde ítems)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    observaciones = models.TextField(blank=True)

    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        default=TipoDocumento.SIN_DOC,
        db_index=True,
    )
    numero_documento = models.CharField(max_length=30, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_documento", "numero_documento"],
                name="uniq_tipo_numero_documento",
                condition=~models.Q(numero_documento=""),
            )
        ]

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente}"

    # -----------------------
    # TOTALES
    # -----------------------
    def recalcular_monto_total(self, guardar=True):
        expr = ExpressionWrapper(
            F("cantidad") * F("precio_unitario"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        total_items = self.items.aggregate(s=Sum(expr))["s"] or Decimal("0.00")
        self.monto_total = total_items
        if guardar:
            self.save(update_fields=["monto_total"])
        return self.monto_total

    @property
    def monto_neto(self):
        total = self.monto_total or Decimal("0")
        return (total / Decimal("1.19")).quantize(Decimal("0.01"))

    @property
    def iva(self):
        return (self.monto_total - self.monto_neto).quantize(Decimal("0.01"))

    # -----------------------
    # COSTO Y MARGEN (estimado por ahora)
    # -----------------------
    @property
    def costo_estimado(self):
        from .services import costo_promedio_kg
        cpk = costo_promedio_kg() or Decimal("0")
        kilos = self.kilos_total or Decimal("0")
        return (kilos * cpk).quantize(Decimal("0.01"))

    @property
    def margen(self):
        # ✅ margen correcto: NETO - COSTO
        return (self.monto_neto - self.costo_estimado).quantize(Decimal("0.01"))

    @property
    def margen_pct(self):
        neto = self.monto_neto
        if neto <= 0:
            return Decimal("0.00")
        return ((self.margen / neto) * Decimal("100")).quantize(Decimal("0.01"))

    # -----------------------
    # KILOS CALCULADOS DESDE ÍTEMS
    # -----------------------
    @property
    def kilos_calculados(self):
        total = Decimal("0.00")
        for it in self.items.select_related("producto"):
            peso = it.producto.peso_kg or Decimal("0")
            total += it.cantidad * peso
        return total


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Importacion(models.Model):
    # ✅ DateField: usa fecha local (no datetime)
    fecha = models.DateField(default=timezone.localdate)

    descripcion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ej: Contenedor Tianjin Sep-2025"
    )

    kilos_ingresados = models.DecimalField(max_digits=12, decimal_places=2)

    # ✅ costo_total SIN IVA (CIF + gastos asociados sin IVA)
    costo_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Costo total CIF + gastos asociados (SIN IVA)"
    )

    costo_por_kg = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    kilos_restantes = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha"]

    def save(self, *args, **kwargs):
        if self.kilos_ingresados and self.kilos_ingresados > 0:
            self.costo_por_kg = (self.costo_total / self.kilos_ingresados).quantize(Decimal("0.01"))

        if not self.pk:
            self.kilos_restantes = self.kilos_ingresados

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha} - {self.descripcion or 'Importación'}"


class GastoOperacional(models.Model):
    class Tipo(models.TextChoices):
        ARRIENDO = "arriendo", "Arriendo"
        BENCINA = "bencina", "Bencina"
        TRANSPORTE = "transporte", "Transporte / despacho"
        SERVICIOS = "servicios", "Servicios"
        CONTADOR = "contador", "Contador"
        MARKETING = "marketing", "Marketing"
        INSUMOS = "insumos", "Insumos"
        OTRO = "otro", "Otro"

    fecha = models.DateField(db_index=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    descripcion = models.CharField(max_length=200, blank=True)

    # ✅ guarda NETO (SIN IVA)
    monto_neto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto NETO (SIN IVA)"
    )

    aplica_iva = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def iva(self):
        if not self.aplica_iva:
            return Decimal("0.00")
        return (self.monto_neto * Decimal("0.19")).quantize(Decimal("0.01"))

    @property
    def total_con_iva(self):
        return (self.monto_neto + self.iva).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.fecha} - {self.get_tipo_display()} - ${self.monto_neto}"
