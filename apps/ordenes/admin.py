from django.contrib import admin

from .models import Cita, EvidenciaFoto, OrdenTrabajo, RepuestoUsado, ServicioOrden


class ServicioOrdenInline(admin.TabularInline):
    model = ServicioOrden
    extra = 0


class RepuestoUsadoInline(admin.TabularInline):
    model = RepuestoUsado
    extra = 0


class EvidenciaFotoInline(admin.TabularInline):
    model = EvidenciaFoto
    extra = 0
    fields = ["imagen", "tipo", "descripcion", "subida_por", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ["id", "taller", "vehiculo", "cliente", "estado", "mecanico", "fecha_ingreso"]
    list_filter = ["taller", "estado"]
    search_fields = ["vehiculo__placa", "cliente__nombre"]
    inlines = [ServicioOrdenInline, RepuestoUsadoInline, EvidenciaFotoInline]


@admin.register(EvidenciaFoto)
class EvidenciaFotoAdmin(admin.ModelAdmin):
    list_display = ["id", "taller", "orden", "tipo", "subida_por", "created_at"]
    list_filter = ["taller", "tipo"]
    search_fields = ["orden__vehiculo__placa"]


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ["id", "taller", "cliente", "vehiculo", "fecha_hora", "estado"]
    list_filter = ["taller", "estado"]
    search_fields = ["cliente__nombre"]
