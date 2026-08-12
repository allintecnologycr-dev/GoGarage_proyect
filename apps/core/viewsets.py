from rest_framework import viewsets

from .permissions import RolEnTaller, TienerTallerActivo


class TenantViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet base para todo modelo que hereda de TenantModel:
    - Filtra automáticamente el queryset por el taller activo de la request.
    - Asigna el taller activo al crear un registro nuevo.
    - Exige TienerTallerActivo + RolEnTaller (este último solo restringe si
      la subclase define `roles_permitidos`).
    """

    permission_classes = [TienerTallerActivo, RolEnTaller]

    def get_queryset(self):
        return super().get_queryset().filter(taller=self.request.taller)

    def perform_create(self, serializer):
        serializer.save(taller=self.request.taller)
