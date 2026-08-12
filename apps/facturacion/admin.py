from django.contrib import admin

from .models import ConfiguracionFacturacionElectronica, DetalleFactura, Factura, Pago


class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 0


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ["numero", "taller", "cliente", "total", "estado", "estado_hacienda", "fecha"]
    list_filter = ["taller", "estado", "estado_hacienda"]
    search_fields = ["numero", "cliente__nombre", "clave_numerica"]
    readonly_fields = [
        "proveedor_fe", "clave_numerica", "consecutivo", "estado_hacienda",
        "mensaje_hacienda", "xml_url", "pdf_url", "fecha_emision_fe",
    ]
    inlines = [DetalleFacturaInline, PagoInline]


@admin.register(ConfiguracionFacturacionElectronica)
class ConfiguracionFacturacionElectronicaAdmin(admin.ModelAdmin):
    list_display = ["taller", "proveedor", "entorno"]
    list_filter = ["proveedor", "entorno"]
    search_fields = ["taller__nombre"]
