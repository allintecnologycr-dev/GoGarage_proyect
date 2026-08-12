from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import DetalleFacturaViewSet, FacturaViewSet, PagoViewSet

router = DefaultRouter()
router.register("facturas", FacturaViewSet, basename="factura")
router.register("detalles-factura", DetalleFacturaViewSet, basename="detalle-factura")
router.register("pagos", PagoViewSet, basename="pago")

urlpatterns = [
    path("", include(router.urls)),
]
