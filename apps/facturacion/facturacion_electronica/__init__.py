from .base import (
    ErrorTransitorioFacturacionElectronica,
    ProveedorFacturacionElectronica,
    ProveedorFacturacionElectronicaError,
    ResultadoEmision,
)
from .hacienda_directo import ProveedorHaciendaDirecto
from .simulado import ProveedorSimulado

_ADAPTADORES = {
    "simulado": ProveedorSimulado,
    "hacienda_directo": ProveedorHaciendaDirecto,
}


def obtener_proveedor(taller) -> ProveedorFacturacionElectronica:
    """
    Resuelve el adaptador configurado para `taller`. Si el taller no tiene
    ConfiguracionFacturacionElectronica todavía, usa el simulado por
    defecto — así un taller nuevo puede probar el flujo de facturación sin
    tener que configurar nada primero.
    """
    configuracion = getattr(taller, "configuracion_fe", None)
    clave_proveedor = configuracion.proveedor if configuracion else "simulado"
    adaptador_cls = _ADAPTADORES.get(clave_proveedor, ProveedorSimulado)
    return adaptador_cls(configuracion)


__all__ = [
    "ErrorTransitorioFacturacionElectronica",
    "ProveedorFacturacionElectronica",
    "ProveedorFacturacionElectronicaError",
    "ProveedorHaciendaDirecto",
    "ProveedorSimulado",
    "ResultadoEmision",
    "obtener_proveedor",
]
