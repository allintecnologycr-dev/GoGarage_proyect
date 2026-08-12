from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Membresia, Taller
from .permissions import TienerTallerActivo
from .serializers import MeSerializer, MembresiaSerializer, TallerSerializer


class MeView(APIView):
    """GET /api/v1/me/ — perfil del usuario autenticado y sus membresías
    (para que el frontend sepa a qué talleres pertenece y con qué rol)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class TallerViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura: un usuario únicamente ve los talleres a los que pertenece."""

    serializer_class = TallerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Taller.objects.filter(membresias__usuario=self.request.user, membresias__activo=True).distinct()


class MembresiaViewSet(viewsets.ModelViewSet):
    """Gestión de membresías del taller activo (alta de miembros del equipo)."""

    serializer_class = MembresiaSerializer
    permission_classes = [IsAuthenticated, TienerTallerActivo]

    def get_queryset(self):
        return Membresia.objects.filter(taller=self.request.taller)

    def perform_create(self, serializer):
        serializer.save(taller=self.request.taller)
