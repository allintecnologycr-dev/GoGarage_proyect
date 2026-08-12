from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import ClienteViewSet, VehiculoViewSet

router = DefaultRouter()
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("vehiculos", VehiculoViewSet, basename="vehiculo")

urlpatterns = [
    path("", include(router.urls)),
]
