from apps.core.viewsets import TenantViewSet

from .models import MovimientoInventario, Repuesto
from .serializers import MovimientoInventarioSerializer, RepuestoSerializer


class RepuestoViewSet(TenantViewSet):
    queryset = Repuesto.objects.all()
    serializer_class = RepuestoSerializer
    search_fields = ["sku", "nombre", "categoria"]
    filterset_fields = ["categoria"]


class MovimientoInventarioViewSet(TenantViewSet):
    queryset = MovimientoInventario.objects.select_related("repuesto", "orden", "usuario").all()
    serializer_class = MovimientoInventarioSerializer
    filterset_fields = ["tipo", "repuesto", "orden"]

    def perform_create(self, serializer):
        serializer.save(taller=self.request.taller, usuario=self.request.user)
