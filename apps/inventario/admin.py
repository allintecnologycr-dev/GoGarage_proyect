from django.contrib import admin

from .models import MovimientoInventario, Repuesto


@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = ["sku", "nombre", "taller", "stock_actual", "stock_minimo", "precio_venta"]
    list_filter = ["taller", "categoria"]
    search_fields = ["sku", "nombre"]


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ["repuesto", "tipo", "cantidad", "taller", "fecha", "usuario"]
    list_filter = ["taller", "tipo"]
    search_fields = ["repuesto__nombre", "repuesto__sku"]
