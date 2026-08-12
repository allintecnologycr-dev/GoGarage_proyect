from django.urls import path

from .views import (
    CotizacionAceptarView,
    CotizacionPublicaDetailView,
    CotizacionRechazarView,
    OrdenPublicaDetailView,
)

urlpatterns = [
    path(
        "cotizaciones/<uuid:token_publico>/",
        CotizacionPublicaDetailView.as_view(),
        name="cotizacion-publica-detalle",
    ),
    path(
        "cotizaciones/<uuid:token_publico>/aceptar/",
        CotizacionAceptarView.as_view(),
        name="cotizacion-publica-aceptar",
    ),
    path(
        "cotizaciones/<uuid:token_publico>/rechazar/",
        CotizacionRechazarView.as_view(),
        name="cotizacion-publica-rechazar",
    ),
    path(
        "ordenes/<uuid:token_seguimiento>/",
        OrdenPublicaDetailView.as_view(),
        name="orden-publica-detalle",
    ),
]
