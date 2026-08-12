"""
Interfaz del adaptador de facturación electrónica (ver docs/ARQUITECTURA.md
secciones 2.4, 5.5 y 8). Cada taller elige su proveedor en
`ConfiguracionFacturacionElectronica.proveedor`; el resto del sistema
(apps/facturacion/tasks.py) solo conoce esta interfaz, nunca un proveedor
concreto — así se puede agregar o cambiar de proveedor sin tocar el resto
del código.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProveedorFacturacionElectronicaError(Exception):
    """Error permanente al emitir: no tiene sentido reintentar (config
    inválida, rechazo definitivo de Hacienda, firma no implementada, etc.)."""


class ErrorTransitorioFacturacionElectronica(ProveedorFacturacionElectronicaError):
    """Error transitorio (timeout, 5xx, red caída): sí vale la pena
    reintentar — ver apps/facturacion/tasks.py:emitir_factura_electronica."""


@dataclass
class ResultadoEmision:
    proveedor: str
    clave_numerica: str
    consecutivo: str
    estado: str  # ver Factura.EstadoHacienda
    mensaje: str = ""
    xml_url: str = ""
    pdf_url: str = ""


class ProveedorFacturacionElectronica(ABC):
    """Adaptador de facturación electrónica para un taller concreto."""

    def __init__(self, configuracion):
        self.configuracion = configuracion

    @abstractmethod
    def emitir(self, factura) -> ResultadoEmision:
        """Emite `factura` (apps.facturacion.models.Factura) ante el
        proveedor. Debe lanzar ErrorTransitorioFacturacionElectronica si el
        error es reintentable, o ProveedorFacturacionElectronicaError para
        cualquier otro fallo permanente."""
        raise NotImplementedError
