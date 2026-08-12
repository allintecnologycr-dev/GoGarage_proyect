from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class Repuesto(TenantModel):
    sku = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=100, blank=True)
    unidad_medida = models.CharField(max_length=20, default="unidad")
    costo_promedio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["taller", "sku"], name="sku_unico_por_taller")
        ]

    def __str__(self):
        return f"{self.sku} — {self.nombre}"


class MovimientoInventario(TenantModel):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"
        AJUSTE = "ajuste", "Ajuste"

    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.IntegerField()
    orden = models.ForeignKey(
        "ordenes.OrdenTrabajo", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_inventario"
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    notas = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo} {self.cantidad} — {self.repuesto}"
