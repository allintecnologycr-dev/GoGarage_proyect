"""
Tarea Celery de emisión de facturas electrónicas (ver docs/ARQUITECTURA.md
secciones 2.4 y 7 — la respuesta del proveedor puede tardar o requerir
reintentos, por eso corre en background y no en el request que cierra la
orden).
"""

from django.utils import timezone

from celery import shared_task

from .facturacion_electronica import ErrorTransitorioFacturacionElectronica, ProveedorFacturacionElectronicaError, obtener_proveedor


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def emitir_factura_electronica(self, factura_id: int) -> str:
    from .models import Factura

    try:
        factura = Factura.objects.select_related("taller", "cliente", "taller__configuracion_fe").get(pk=factura_id)
    except Factura.DoesNotExist:
        return f"Factura {factura_id} no existe"

    proveedor = obtener_proveedor(factura.taller)

    try:
        resultado = proveedor.emitir(factura)
    except ErrorTransitorioFacturacionElectronica as exc:
        raise self.retry(exc=exc)
    except ProveedorFacturacionElectronicaError as exc:
        factura.estado_hacienda = Factura.EstadoHacienda.ERROR
        factura.mensaje_hacienda = str(exc)
        factura.save(update_fields=["estado_hacienda", "mensaje_hacienda"])
        return f"Factura {factura_id}: error permanente al emitir — {exc}"

    factura.proveedor_fe = resultado.proveedor
    factura.clave_numerica = resultado.clave_numerica
    factura.consecutivo = resultado.consecutivo
    factura.estado_hacienda = resultado.estado
    factura.mensaje_hacienda = resultado.mensaje
    factura.xml_url = resultado.xml_url
    factura.pdf_url = resultado.pdf_url
    factura.fecha_emision_fe = timezone.now()
    factura.save(
        update_fields=[
            "proveedor_fe", "clave_numerica", "consecutivo", "estado_hacienda",
            "mensaje_hacienda", "xml_url", "pdf_url", "fecha_emision_fe",
        ]
    )
    return f"Factura {factura_id}: {resultado.estado}"
