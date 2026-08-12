import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import Membresia
from apps.core.permissions import RolEnTaller, TienerTallerActivo
from apps.core.viewsets import TenantViewSet

from .models import ConfiguracionFacturacionElectronica, DetalleFactura, Factura, Pago
from .serializers import (
    ConfiguracionFacturacionElectronicaSerializer,
    DetalleFacturaSerializer,
    FacturaSerializer,
    GenerarFacturaSerializer,
    PagoSerializer,
)
from .tasks import emitir_factura_electronica

logger = logging.getLogger(__name__)


class FacturaViewSet(TenantViewSet):
    queryset = Factura.objects.select_related("cliente", "orden", "cotizacion").all()
    serializer_class = FacturaSerializer
    search_fields = ["numero", "cliente__nombre"]
    filterset_fields = ["estado", "estado_hacienda", "cliente", "orden"]
    # Solo admin/contable pueden anular o crear facturas manualmente.
    roles_permitidos = [Membresia.Rol.ADMIN_TALLER, Membresia.Rol.CONTABLE]

    @action(detail=False, methods=["post"], url_path="generar-desde-orden")
    def generar_desde_orden(self, request):
        """Cierra la orden y genera+emite su factura (ver docs/ARQUITECTURA.md sección 2.4)."""
        serializer = GenerarFacturaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        factura = serializer.save()

        try:
            emitir_factura_electronica.delay(factura.id)
        except Exception:
            # Igual que con la notificación de cotizaciones: si Celery/Redis
            # no está disponible, la factura queda creada en estado
            # "pendiente de envío" y se puede reintentar la emisión luego
            # (ver acción `emitir` más abajo) en vez de bloquear el cierre.
            logger.exception("No se pudo encolar emitir_factura_electronica para %s", factura.id)

        return Response(FacturaSerializer(factura).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="emitir")
    def emitir(self, request, pk=None):
        """Reintenta la emisión electrónica de una factura ya creada."""
        factura = self.get_object()
        try:
            emitir_factura_electronica.delay(factura.id)
        except Exception:
            logger.exception("No se pudo encolar emitir_factura_electronica para %s", factura.id)
            return Response(
                {"detail": "No se pudo encolar la emisión (¿Celery/Redis está corriendo?)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(self.get_serializer(factura).data)


class ConfiguracionFacturacionElectronicaViewSet(TenantViewSet):
    queryset = ConfiguracionFacturacionElectronica.objects.all()
    serializer_class = ConfiguracionFacturacionElectronicaSerializer
    roles_permitidos = [Membresia.Rol.ADMIN_TALLER]


class _FacturaScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [TienerTallerActivo, RolEnTaller]

    def get_queryset(self):
        return super().get_queryset().filter(factura__taller=self.request.taller)


class DetalleFacturaViewSet(_FacturaScopedViewSet):
    queryset = DetalleFactura.objects.select_related("factura")
    serializer_class = DetalleFacturaSerializer
    filterset_fields = ["factura"]


class PagoViewSet(_FacturaScopedViewSet):
    queryset = Pago.objects.select_related("factura")
    serializer_class = PagoSerializer
    filterset_fields = ["factura", "metodo"]
