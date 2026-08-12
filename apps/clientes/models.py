from django.db import models

from apps.core.models import TenantModel


class Cliente(TenantModel):
    nombre = models.CharField(max_length=150)
    identificacion = models.CharField(max_length=50, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["nombre"]
        indexes = [models.Index(fields=["taller", "nombre"])]

    def __str__(self):
        return self.nombre


class Vehiculo(TenantModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="vehiculos")
    placa = models.CharField(max_length=20)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.PositiveIntegerField(null=True, blank=True)
    vin = models.CharField(max_length=50, blank=True)
    kilometraje_actual = models.PositiveIntegerField(default=0)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ["placa"]
        indexes = [models.Index(fields=["taller", "placa"])]
        constraints = [
            models.UniqueConstraint(fields=["taller", "placa"], name="placa_unica_por_taller")
        ]

    def __str__(self):
        return f"{self.placa} — {self.marca} {self.modelo}"
