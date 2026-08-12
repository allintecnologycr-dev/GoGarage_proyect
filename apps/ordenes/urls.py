from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import (
    CitaViewSet,
    EvidenciaFotoViewSet,
    OrdenTrabajoViewSet,
    RepuestoUsadoViewSet,
    ServicioOrdenViewSet,
)

router = DefaultRouter()
router.register("ordenes", OrdenTrabajoViewSet, basename="orden")
router.register("citas", CitaViewSet, basename="cita")
router.register("servicios-orden", ServicioOrdenViewSet, basename="servicio-orden")
router.register("repuestos-usados", RepuestoUsadoViewSet, basename="repuesto-usado")
router.register("evidencias-foto", EvidenciaFotoViewSet, basename="evidencia-foto")

urlpatterns = [
    path("", include(router.urls)),
]
