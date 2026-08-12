from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import MovimientoInventarioViewSet, RepuestoViewSet

router = DefaultRouter()
router.register("repuestos", RepuestoViewSet, basename="repuesto")
router.register("movimientos-inventario", MovimientoInventarioViewSet, basename="movimiento-inventario")

urlpatterns = [
    path("", include(router.urls)),
]
