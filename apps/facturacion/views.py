from rest_framework import viewsets

from apps.core.models import Membresia
from apps.core.permissions import RolEnTaller, TienerTallerActivo
from apps.core.viewsets import TenantViewSet

from .models import DetalleFactura, Factura, Pago
from .serializers import DetalleFacturaSerializer, FacturaSerializer, PagoSerializer


class FacturaViewSet(TenantViewSet):
    queryset = Factura.objects.select_related("cliente", "orden").all()
    serializer_class = FacturaSerializer
    search_fields = ["numero", "cliente__nombre"]
    filterset_fields = ["estado", "cliente"]
    # Solo admin/contable pueden anular o crear facturas manualmente.
    roles_permitidos = [Membresia.Rol.ADMIN_TALLER, Membresia.Rol.CONTABLE]


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
