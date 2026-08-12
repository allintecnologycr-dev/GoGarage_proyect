from rest_framework.permissions import BasePermission

from .tenancy import resolver_taller_activo


class TienerTallerActivo(BasePermission):
    """
    Resuelve el taller activo de la request (dejándolo en request.taller /
    request.membresia) y exige que se haya podido determinar uno.
    Debe listarse ANTES que RolEnTaller en `permission_classes`, ya que
    RolEnTaller depende de que este haya corrido primero.
    """

    message = "No se pudo determinar el taller activo. Envíe el header X-Taller-Id."

    def has_permission(self, request, view):
        taller, membresia = resolver_taller_activo(request)
        request.taller = taller
        request.membresia = membresia
        return bool(taller)


class RolEnTaller(BasePermission):
    """
    Permite restringir un ViewSet a ciertos roles del taller activo.
    Uso: agregar `roles_permitidos = [Membresia.Rol.ADMIN_TALLER]` al ViewSet.
    Si el ViewSet no define `roles_permitidos`, cualquier rol pasa.
    Requiere que TienerTallerActivo haya corrido antes (ver arriba).
    """

    def has_permission(self, request, view):
        membresia = getattr(request, "membresia", None)
        if membresia is None:
            return False
        roles_permitidos = getattr(view, "roles_permitidos", None)
        if not roles_permitidos:
            return True
        return membresia.rol in roles_permitidos
