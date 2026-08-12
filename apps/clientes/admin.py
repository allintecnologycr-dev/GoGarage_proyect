from django.contrib import admin

from .models import Cliente, Vehiculo


class VehiculoInline(admin.TabularInline):
    model = Vehiculo
    extra = 0
    fields = ["placa", "marca", "modelo", "anio", "kilometraje_actual"]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nombre", "taller", "telefono", "email"]
    list_filter = ["taller"]
    search_fields = ["nombre", "identificacion", "telefono", "email"]
    inlines = [VehiculoInline]


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ["placa", "marca", "modelo", "cliente", "taller", "kilometraje_actual"]
    list_filter = ["taller", "marca"]
    search_fields = ["placa", "vin", "cliente__nombre"]
