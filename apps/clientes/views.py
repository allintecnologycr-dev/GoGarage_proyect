from apps.core.viewsets import TenantViewSet

from .models import Cliente, Vehiculo
from .serializers import ClienteSerializer, VehiculoSerializer


class ClienteViewSet(TenantViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    search_fields = ["nombre", "identificacion", "telefono", "email"]
    filterset_fields = []


class VehiculoViewSet(TenantViewSet):
    queryset = Vehiculo.objects.select_related("cliente").all()
    serializer_class = VehiculoSerializer
    search_fields = ["placa", "marca", "modelo", "vin"]
    filterset_fields = ["cliente"]
