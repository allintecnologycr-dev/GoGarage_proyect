"""Adaptador simulado: no llama a ningún servicio externo. Sirve para
desarrollar y demostrar el flujo completo (cerrar orden -> generar factura
-> emitir -> Celery) sin depender de credenciales reales de Hacienda o de
un PAC. Es el proveedor por defecto de ConfiguracionFacturacionElectronica."""

import uuid
from datetime import datetime, timezone as dt_timezone

from .base import ProveedorFacturacionElectronica, ResultadoEmision


class ProveedorSimulado(ProveedorFacturacionElectronica):
    def emitir(self, factura) -> ResultadoEmision:
        ahora = datetime.now(dt_timezone.utc)
        clave_simulada = f"SIMULADA-{ahora:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:12]}"
        return ResultadoEmision(
            proveedor="simulado",
            clave_numerica=clave_simulada,
            consecutivo=factura.numero,
            estado="aceptada",
            mensaje="Emisión simulada: no se contactó a Hacienda ni a ningún PAC.",
        )
