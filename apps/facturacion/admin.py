from django.contrib import admin

from .models import DetalleFactura, Factura, Pago


class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 0


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ["numero", "taller", "cliente", "total", "estado", "fecha"]
    list_filter = ["taller", "estado"]
    search_fields = ["numero", "cliente__nombre"]
    inlines = [DetalleFacturaInline, PagoInline]
