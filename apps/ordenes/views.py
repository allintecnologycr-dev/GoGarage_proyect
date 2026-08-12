from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import RolEnTaller, TienerTallerActivo
from apps.core.viewsets import TenantViewSet

from .models import Cita, Cotizacion, DetalleCotizacion, EvidenciaFoto, OrdenTrabajo, RepuestoUsado, ServicioOrden
from .serializers import (
    CitaSerializer,
    CotizacionSerializer,
    DetalleCotizacionSerializer,
    EvidenciaFotoSerializer,
    OrdenTrabajoSerializer,
    RecepcionRapidaSerializer,
    RepuestoUsadoSerializer,
    ServicioOrdenSerializer,
)


class OrdenTrabajoViewSet(TenantViewSet):
    queryset = OrdenTrabajo.objects.select_related("vehiculo", "cliente", "mecanico").all()
    serializer_class = OrdenTrabajoSerializer
    search_fields = ["vehiculo__placa", "cliente__nombre"]
    filterset_fields = ["estado", "vehiculo", "cliente", "mecanico"]

    @action(detail=False, methods=["post"], url_path="recepcion-rapida")
    def recepcion_rapida(self, request):
        """Alta rápida de orden por placa (ver docs/ARQUITECTURA.md sección 2.1)."""
        serializer = RecepcionRapidaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        orden = serializer.save()
        data = OrdenTrabajoSerializer(orden, context={"request": request}).data
        data["vehiculo_nuevo"] = orden.vehiculo_nuevo
        return Response(data, status=status.HTTP_201_CREATED)


class EvidenciaFotoViewSet(TenantViewSet):
    queryset = EvidenciaFoto.objects.select_related("orden", "subida_por").all()
    serializer_class = EvidenciaFotoSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["orden", "tipo"]

    def perform_create(self, serializer):
        serializer.save(taller=self.request.taller, subida_por=self.request.user)


class CotizacionViewSet(TenantViewSet):
    queryset = Cotizacion.objects.select_related("orden__vehiculo", "cliente").prefetch_related("detalles").all()
    serializer_class = CotizacionSerializer
    search_fields = ["cliente__nombre", "orden__vehiculo__placa"]
    filterset_fields = ["estado", "orden", "cliente"]

    @action(detail=True, methods=["post"], url_path="enviar")
    def enviar(self, request, pk=None):
        """Marca la cotización como enviada (queda lista para compartir el link)."""
        cotizacion = self.get_object()
        if cotizacion.estado != Cotizacion.Estado.BORRADOR:
            return Response(
                {"detail": "Solo una cotización en borrador se puede marcar como enviada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cotizacion.estado = Cotizacion.Estado.ENVIADA
        cotizacion.save(update_fields=["estado"])
        return Response(self.get_serializer(cotizacion).data)


class DetalleCotizacionViewSet(viewsets.ModelViewSet):
    """Sub-recurso de una cotización: se filtra por `cotizacion__taller`
    porque no lleva `taller` propio (igual que servicios/repuestos de orden)."""

    queryset = DetalleCotizacion.objects.select_related("cotizacion")
    serializer_class = DetalleCotizacionSerializer
    permission_classes = [TienerTallerActivo, RolEnTaller]
    filterset_fields = ["cotizacion"]

    def get_queryset(self):
        return super().get_queryset().filter(cotizacion__taller=self.request.taller)


class CitaViewSet(TenantViewSet):
    queryset = Cita.objects.select_related("cliente", "vehiculo").all()
    serializer_class = CitaSerializer
    search_fields = ["cliente__nombre", "motivo"]
    filterset_fields = ["estado", "cliente"]


class _OrdenScopedViewSet(viewsets.ModelViewSet):
    """Base para sub-recursos de una orden (servicios, repuestos usados):
    se filtran a través de `orden__taller` porque no llevan `taller` propio."""

    permission_classes = [TienerTallerActivo, RolEnTaller]

    def get_queryset(self):
        return super().get_queryset().filter(orden__taller=self.request.taller)


class ServicioOrdenViewSet(_OrdenScopedViewSet):
    queryset = ServicioOrden.objects.select_related("orden")
    serializer_class = ServicioOrdenSerializer
    filterset_fields = ["orden"]


class RepuestoUsadoViewSet(_OrdenScopedViewSet):
    queryset = RepuestoUsado.objects.select_related("orden", "repuesto")
    serializer_class = RepuestoUsadoSerializer
    filterset_fields = ["orden"]
