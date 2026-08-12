from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import MeView, MembresiaViewSet, TallerViewSet

router = DefaultRouter()
router.register("talleres", TallerViewSet, basename="taller")
router.register("membresias", MembresiaViewSet, basename="membresia")

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
