from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import RolEnTaller, TienerTallerActivo
from apps.core.viewsets import TenantViewSet

from .models import Cita, EvidenciaFoto, OrdenTrabajo, RepuestoUsado, ServicioOrden
from .serializers import (
    CitaSerializer,
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
