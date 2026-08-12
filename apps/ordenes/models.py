import uuid

from django.conf import settings
from django.db import models

from apps.clientes.models import Cliente, Vehiculo
from apps.core.models import TenantModel


class OrdenTrabajo(TenantModel):
    class Estado(models.TextChoices):
        RECIBIDO = "recibido", "Recibido"
        EN_DIAGNOSTICO = "en_diagnostico", "En diagnóstico"
        EN_REPARACION = "en_reparacion", "En reparación"
        ESPERANDO_REPUESTO = "esperando_repuesto", "Esperando repuesto"
        LISTO = "listo", "Listo"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name="ordenes")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordenes")
    mecanico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_asignadas"
    )
    estado = models.CharField(max_length=25, choices=Estado.choices, default=Estado.RECIBIDO)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_estimada_entrega = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    kilometraje_ingreso = models.PositiveIntegerField(null=True, blank=True)
    diagnostico = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_ingreso"]
        indexes = [models.Index(fields=["taller", "estado"])]

    def __str__(self):
        return f"Orden #{self.pk} — {self.vehiculo}"


def ruta_evidencia_foto(instance, filename):
    return f"evidencias/taller_{instance.taller_id}/orden_{instance.orden_id}/{uuid.uuid4().hex}_{filename}"


class EvidenciaFoto(TenantModel):
    """Foto de una orden (ingreso, daños, avances, entrega) subida desde el
    celular. El archivo vive en Supabase Storage (ver config/settings/base.py:STORAGES)."""

    class Tipo(models.TextChoices):
        INGRESO = "ingreso", "Ingreso"
        DIAGNOSTICO = "diagnostico", "Diagnóstico"
        REPARACION = "reparacion", "Reparación"
        ENTREGA = "entrega", "Entrega"

    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="evidencias_foto")
    imagen = models.ImageField(upload_to=ruta_evidencia_foto)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.INGRESO)
    descripcion = models.CharField(max_length=255, blank=True)
    subida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias_subidas"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["taller", "orden"])]

    def __str__(self):
        return f"Foto {self.tipo} — orden #{self.orden_id}"


class ServicioOrden(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="servicios")
    descripcion = models.CharField(max_length=255)
    horas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.descripcion


class RepuestoUsado(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="repuestos_usados")
    repuesto = models.ForeignKey("inventario.Repuesto", on_delete=models.PROTECT, related_name="usos")
    cantidad = models.PositiveIntegerField(default=1)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.repuesto}"


class Cita(TenantModel):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        CUMPLIDA = "cumplida", "Cumplida"
        CANCELADA = "cancelada", "Cancelada"
        NO_SHOW = "no_show", "No se presentó"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="citas")
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="citas"
    )
    fecha_hora = models.DateTimeField()
    motivo = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    orden_generada = models.ForeignKey(
        OrdenTrabajo, on_delete=models.SET_NULL, null=True, blank=True, related_name="cita_origen"
    )

    class Meta:
        ordering = ["fecha_hora"]
        indexes = [models.Index(fields=["taller", "fecha_hora"])]

    def __str__(self):
        return f"Cita {self.cliente} — {self.fecha_hora:%Y-%m-%d %H:%M}"
