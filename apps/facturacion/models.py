from django.db import models

from apps.clientes.models import Cliente
from apps.core.models import TenantModel


class Factura(TenantModel):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADA = "pagada", "Pagada"
        ANULADA = "anulada", "Anulada"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="facturas")
    orden = models.ForeignKey(
        "ordenes.OrdenTrabajo", on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas"
    )
    numero = models.CharField(max_length=30)
    fecha = models.DateField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)

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
