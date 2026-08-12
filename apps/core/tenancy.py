"""
Resolución del taller (tenant) activo para una request de la API.

Importante: esto se invoca desde permission classes de DRF (no desde
middleware de Django), porque la autenticación JWT ocurre dentro del ciclo
de `dispatch()` de DRF — en el middleware de Django, `request.user` todavía
no refleja al usuario del token.
"""

from .models import Membresia


def resolver_taller_activo(request):
    """
    Devuelve (taller, membresia) para la request autenticada, o (None, None)
    si no se pudo determinar. Nunca confía en un tenant_id sin verificar
    que el usuario tenga una Membresia activa en él.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None, None

    membresias = Membresia.objects.filter(usuario=user, activo=True).select_related("taller")

    taller_id_header = request.headers.get("X-Taller-Id")
    if taller_id_header:
        membresia = membresias.filter(taller_id=taller_id_header).first()
    elif membresias.count() == 1:
        membresia = membresias.first()
    else:
        membresia = None

    if membresia is None:
        return None, None
    return membresia.taller, membresia
