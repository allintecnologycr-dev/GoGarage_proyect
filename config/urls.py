"""
Configuración de URLs raíz de GoGarage.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.clientes.urls")),
    path("api/v1/", include("apps.ordenes.urls")),
    path("api/v1/", include("apps.inventario.urls")),
    path("api/v1/", include("apps.facturacion.urls")),
]

if settings.DEBUG:
    # Solo relevante cuando se usa el fallback de disco local (sin Supabase
    # Storage configurado); con S3/Supabase las URLs de media apuntan al bucket.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
