import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.ordenes.models import Cotizacion, OrdenTrabajo
from apps.ordenes.tasks import notificar_respuesta_cotizacion

from .serializers import CotizacionPublicaSerializer, OrdenPublicaSerializer

logger = logging.getLogger(__name__)

TEMPLATE_DETALLE = "publico/cotizacion_detalle.html"
TEMPLATE_ORDEN = "publico/orden_detalle.html"

_QUERYSET_BASE = Cotizacion.objects.select_related(
    "taller", "cliente", "orden__vehiculo"
).prefetch_related("detalles")

_QUERYSET_ORDEN = OrdenTrabajo.objects.select_related("taller", "vehiculo").prefetch_related("evidencias_foto")


def _vencer_si_corresponde(cotizacion):
    """Auto-expira una cotización vieja al leerla, sin esperar a Celery beat."""
    if cotizacion.vencida and cotizacion.estado in (Cotizacion.Estado.BORRADOR, Cotizacion.Estado.ENVIADA):
        Cotizacion.objects.filter(pk=cotizacion.pk).update(estado=Cotizacion.Estado.VENCIDA)
        cotizacion.estado = Cotizacion.Estado.VENCIDA


class CotizacionPublicaDetailView(APIView):
    """
    GET /api/v1/public/cotizaciones/<token>/ — detalle de solo lectura.
    Resuelve por `token_publico` (UUIDv4 no adivinable), nunca por `id` ni
    `placa` (ver docs/ARQUITECTURA.md sección 8). Renderiza HTML para el
    navegador (el link que se comparte por WhatsApp) o JSON para clientes
    de API, según el Accept header — mismo endpoint documentado en 6.4.
    """

    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "publico"

    def get(self, request, token_publico):
        cotizacion = get_object_or_404(_QUERYSET_BASE, token_publico=token_publico)
        _vencer_si_corresponde(cotizacion)
        data = CotizacionPublicaSerializer(cotizacion).data
        if request.accepted_renderer.format == "html":
            return Response(data, template_name=TEMPLATE_DETALLE)
        return Response(data)


class _CotizacionRespuestaView(APIView):
    """Base para aceptar/rechazar desde el link público."""

    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "publico"
    nuevo_estado = None

    def post(self, request, token_publico):
        cotizacion = get_object_or_404(_QUERYSET_BASE, token_publico=token_publico)
        _vencer_si_corresponde(cotizacion)

        aplicada = cotizacion.respondible
        if aplicada:
            cotizacion.estado = self.nuevo_estado
            cotizacion.fecha_respuesta = timezone.now()
            cotizacion.save(update_fields=["estado", "fecha_respuesta"])
            try:
                notificar_respuesta_cotizacion.delay(cotizacion.id)
            except Exception:
                # La notificación interna es un efecto secundario: si Celery/Redis
                # no está disponible, no debe impedir que el cliente pueda
                # aceptar/rechazar su cotización.
                logger.exception("No se pudo encolar notificar_respuesta_cotizacion para %s", cotizacion.id)

        data = CotizacionPublicaSerializer(cotizacion).data
        status_code = status.HTTP_200_OK if aplicada else status.HTTP_409_CONFLICT
        if request.accepted_renderer.format == "html":
            return Response(data, template_name=TEMPLATE_DETALLE, status=status_code)
        return Response(data, status=status_code)


class CotizacionAceptarView(_CotizacionRespuestaView):
    nuevo_estado = Cotizacion.Estado.ACEPTADA


class CotizacionRechazarView(_CotizacionRespuestaView):
    nuevo_estado = Cotizacion.Estado.RECHAZADA


class OrdenPublicaDetailView(APIView):
    """
    GET /api/v1/public/ordenes/<token_seguimiento>/ — estado actual de la
    orden, línea de tiempo y fotos (ver docs/ARQUITECTURA.md sección 2.3).
    Solo lectura: no hay acciones que el cliente pueda disparar acá, a
    diferencia de la cotización.
    """

    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "publico"

    def get(self, request, token_seguimiento):
        orden = get_object_or_404(_QUERYSET_ORDEN, token_seguimiento=token_seguimiento)
        data = OrdenPublicaSerializer(orden).data
        if request.accepted_renderer.format == "html":
            return Response(data, template_name=TEMPLATE_ORDEN)
        return Response(data)
