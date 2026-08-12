from decimal import Decimal

from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.clientes.models import Cliente
from apps.core.models import TenantModel, TimestampedModel


class ConfiguracionFacturacionElectronica(TimestampedModel):
    """
    Credenciales de facturación electrónica de un taller. Van por taller
    (no en settings globales) porque cada taller es un contribuyente
    distinto ante Hacienda, con su propio usuario ATV y certificado.

    NOTA DE SEGURIDAD: usuario/contraseña ATV y la contraseña del .p12 se
    guardan en texto plano, igual que el resto del scaffold actual (ver
    supabase.txt). Para producción esto debería vivir en un gestor de
    secretos, no en la base de datos tal cual.
    """

    class Proveedor(models.TextChoices):
        SIMULADO = "simulado", "Simulado (desarrollo/demo, no llama a Hacienda)"
        HACIENDA_DIRECTO = "hacienda_directo", "Hacienda directo (ATV)"

    class Entorno(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox / pruebas"
        PRODUCCION = "produccion", "Producción"

    taller = models.OneToOneField("core.Taller", on_delete=models.CASCADE, related_name="configuracion_fe")
    proveedor = models.CharField(max_length=30, choices=Proveedor.choices, default=Proveedor.SIMULADO)
    entorno = models.CharField(max_length=15, choices=Entorno.choices, default=Entorno.SANDBOX)

    # Solo aplican a proveedor=hacienda_directo (ver apps/facturacion/facturacion_electronica/hacienda_directo.py)
    usuario_atv = models.CharField(max_length=150, blank=True)
    contrasena_atv = models.CharField(max_length=150, blank=True)
    client_id_atv = models.CharField(max_length=50, blank=True, default="api-stag")
    certificado_p12_path = models.CharField(
        max_length=255, blank=True,
        help_text="Ruta local al .p12 en el servidor (fuera de git y de storage público). No implementado aún.",
    )
    certificado_p12_password = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Config FE — {self.taller} ({self.get_proveedor_display()})"


class Factura(TenantModel):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADA = "pagada", "Pagada"
        ANULADA = "anulada", "Anulada"

    class EstadoHacienda(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de envío"
        ENVIADA = "enviada", "Enviada, esperando respuesta"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        ERROR = "error", "Error al emitir"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="facturas")
    orden = models.ForeignKey(
        "ordenes.OrdenTrabajo", on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas"
    )
    cotizacion = models.ForeignKey(
        "ordenes.Cotizacion", on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas"
    )
    numero = models.CharField(max_length=30)
    fecha = models.DateField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)

    # Facturación electrónica (ver docs/ARQUITECTURA.md sección 5.5 y 2.4)
    proveedor_fe = models.CharField(max_length=30, blank=True)
    clave_numerica = models.CharField(max_length=50, null=True, blank=True, default=None, unique=True)
    consecutivo = models.CharField(max_length=20, blank=True)
    estado_hacienda = models.CharField(max_length=15, choices=EstadoHacienda.choices, default=EstadoHacienda.PENDIENTE)
    mensaje_hacienda = models.TextField(blank=True)
    xml_url = models.URLField(blank=True)
    pdf_url = models.URLField(blank=True)
    fecha_emision_fe = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        constraints = [
            models.UniqueConstraint(fields=["taller", "numero"], name="numero_factura_unico_por_taller")
        ]

    def __str__(self):
        return f"Factura {self.numero}"


class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="detalles")
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return self.descripcion


@receiver([post_save, post_delete], sender=DetalleFactura)
def _recalcular_totales_factura(sender, instance, **kwargs):
    """Mismo patrón que DetalleCotizacion en apps.ordenes: mantiene
    Factura.subtotal/total en línea con sus detalles."""
    factura = instance.factura
    subtotal = sum((detalle.subtotal for detalle in factura.detalles.all()), Decimal("0"))
    Factura.objects.filter(pk=factura.pk).update(subtotal=subtotal, total=subtotal + factura.impuestos)


class Pago(models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia"
        SINPE = "sinpe", "SINPE"

    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="pagos")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=Metodo.choices)
    fecha = models.DateTimeField(auto_now_add=True)
    referencia = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Pago {self.monto} — {self.factura}"
