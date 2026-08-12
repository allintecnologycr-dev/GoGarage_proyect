"""
Adaptador directo contra Hacienda (ATV) — Costa Rica, Factura Electrónica
v4.3. Implementa el flujo real de OAuth 2.0 y las llamadas HTTP a los
endpoints oficiales, PERO la firma XAdES-BES del XML (paso obligatorio
antes de poder enviar cualquier comprobante) queda pendiente: no hay
certificado .p12 real disponible para implementarla y probarla, y firmar
"a ciegas" sin poder validar contra el sandbox de Hacienda es el tipo de
bug que se traduce en un rechazo fiscal real, no un error de UI.

Lo que SÍ funciona tal cual está (no depende del .p12):
- Autenticación OAuth 2.0 contra el IDP de Hacienda (usuario/contraseña).
- Armado de la clave numérica de 50 dígitos.
- Armado del XML v4.3 con los datos de la factura (sin firmar).

Lo que falta (ver _firmar_xml):
- Firma XAdES-BES con el .p12 del contribuyente.
- Validar la estructura exacta del XML contra el Anexo v4.3 vigente y los
  códigos CAByS por línea de detalle (DetalleFactura no los modela todavía).

Cuando haya certificado y credenciales de sandbox reales, completar
_firmar_xml y probar contra HACIENDA_URLS["sandbox"] antes de tocar producción.
"""

import random
from datetime import datetime, timezone as dt_timezone
from xml.etree import ElementTree as ET

import requests

from .base import (
    ErrorTransitorioFacturacionElectronica,
    ProveedorFacturacionElectronica,
    ProveedorFacturacionElectronicaError,
    ResultadoEmision,
)

# Endpoints oficiales de Hacienda (públicos, no son secretos — a diferencia
# de las credenciales del contribuyente, que sí viven en
# ConfiguracionFacturacionElectronica).
HACIENDA_URLS = {
    "sandbox": {
        "oauth": "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token",
        "recepcion": "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion/",
    },
    "produccion": {
        "oauth": "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token",
        "recepcion": "https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/",
    },
}

TIPO_DOCUMENTO_FACTURA_ELECTRONICA = "01"


class ProveedorHaciendaDirecto(ProveedorFacturacionElectronica):
    def emitir(self, factura) -> ResultadoEmision:
        config = self.configuracion
        if not config or not config.usuario_atv or not config.contrasena_atv:
            raise ProveedorFacturacionElectronicaError(
                "Falta configurar usuario_atv/contrasena_atv en ConfiguracionFacturacionElectronica del taller."
            )

        token = self._obtener_token(config)
        clave = self._generar_clave_numerica(factura, config)
        xml_sin_firmar = self._generar_xml(factura, clave)
        # A partir de acá se necesita el .p12 real — ver docstring del módulo.
        xml_firmado = self._firmar_xml(xml_sin_firmar, config)
        respuesta = self._enviar_comprobante(clave, xml_firmado, token, config)
        return respuesta

    def _obtener_token(self, config) -> str:
        url = HACIENDA_URLS[config.entorno]["oauth"]
        try:
            resp = requests.post(
                url,
                data={
                    "grant_type": "password",
                    "client_id": config.client_id_atv or "api-stag",
                    "username": config.usuario_atv,
                    "password": config.contrasena_atv,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise ErrorTransitorioFacturacionElectronica(f"No se pudo contactar el IDP de Hacienda: {exc}") from exc

        if resp.status_code >= 500:
            raise ErrorTransitorioFacturacionElectronica(f"IDP de Hacienda respondió {resp.status_code}")
        if resp.status_code != 200:
            raise ProveedorFacturacionElectronicaError(
                f"Autenticación rechazada por Hacienda ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.json()["access_token"]

    def _generar_clave_numerica(self, factura, config) -> str:
        """
        Clave de 50 dígitos según el Anexo v4.3:
        país(3) + día(2) + mes(2) + año(2) + cédula emisor(12) +
        consecutivo(20: sucursal 3 + terminal 5 + tipo doc 2 + secuencial 10)
        + situación comprobante(1) + código de seguridad(8).

        NOTA: implementado de memoria a partir de la especificación pública,
        sin poder validarlo contra el sandbox real — revisar contra el
        Anexo vigente antes de usar en producción.
        """
        ahora = datetime.now(dt_timezone.utc)
        pais = "506"
        dia, mes, anio = f"{ahora.day:02d}", f"{ahora.month:02d}", f"{ahora.year % 100:02d}"

        cedula = "".join(ch for ch in (factura.taller.identificacion_fiscal or "") if ch.isdigit())
        if not cedula:
            raise ProveedorFacturacionElectronicaError(
                "El taller no tiene identificacion_fiscal (cédula jurídica) configurada."
            )
        cedula = cedula.rjust(12, "0")[-12:]

        sucursal = "001"
        terminal = "00001"
        numero_secuencial = "".join(ch for ch in factura.numero if ch.isdigit()).rjust(10, "0")[-10:]
        consecutivo = f"{sucursal}{terminal}{TIPO_DOCUMENTO_FACTURA_ELECTRONICA}{numero_secuencial}"

        situacion = "1"  # normal (no contingencia, no sin-internet)
        codigo_seguridad = f"{random.randint(0, 99999999):08d}"

        clave = f"{pais}{dia}{mes}{anio}{cedula}{consecutivo}{situacion}{codigo_seguridad}"
        assert len(clave) == 50, f"clave numérica mal formada: {len(clave)} dígitos"
        return clave

    def _generar_xml(self, factura, clave: str) -> bytes:
        """
        Esqueleto del XML v4.3 con los nodos principales. No incluye
        códigos CAByS por línea (DetalleFactura no los modela todavía) ni
        el desglose completo de impuestos por línea — hay que completarlo
        contra el Anexo real antes de firmar/enviar.
        """
        root = ET.Element("FacturaElectronica", xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3")
        ET.SubElement(root, "Clave").text = clave
        ET.SubElement(root, "NumeroConsecutivo").text = factura.numero
        ET.SubElement(root, "FechaEmision").text = factura.fecha.isoformat()

        emisor = ET.SubElement(root, "Emisor")
        ET.SubElement(emisor, "Nombre").text = factura.taller.nombre
        identificacion_emisor = ET.SubElement(emisor, "Identificacion")
        ET.SubElement(identificacion_emisor, "Tipo").text = "02"  # cédula jurídica
        ET.SubElement(identificacion_emisor, "Numero").text = factura.taller.identificacion_fiscal

        receptor = ET.SubElement(root, "Receptor")
        ET.SubElement(receptor, "Nombre").text = factura.cliente.nombre
        if factura.cliente.identificacion:
            identificacion_receptor = ET.SubElement(receptor, "Identificacion")
            ET.SubElement(identificacion_receptor, "Numero").text = factura.cliente.identificacion

        detalle_servicio = ET.SubElement(root, "DetalleServicio")
        for i, detalle in enumerate(factura.detalles.all(), start=1):
            linea = ET.SubElement(detalle_servicio, "LineaDetalle")
            ET.SubElement(linea, "NumeroLinea").text = str(i)
            # TODO: CodigoCAByS real por línea — pendiente de modelar en DetalleFactura/Repuesto.
            ET.SubElement(linea, "Cantidad").text = str(detalle.cantidad)
            ET.SubElement(linea, "Detalle").text = detalle.descripcion
            ET.SubElement(linea, "PrecioUnitario").text = str(detalle.precio_unitario)
            ET.SubElement(linea, "MontoTotal").text = str(detalle.subtotal)

        resumen = ET.SubElement(root, "ResumenFactura")
        ET.SubElement(resumen, "TotalVentaNeta").text = str(factura.subtotal)
        ET.SubElement(resumen, "TotalImpuesto").text = str(factura.impuestos)
        ET.SubElement(resumen, "TotalComprobante").text = str(factura.total)

        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _firmar_xml(self, xml_sin_firmar: bytes, config) -> bytes:
        """
        TODO(facturacion-electronica): firmar `xml_sin_firmar` con el
        certificado .p12 del taller usando el estándar XAdES-BES.

        No implementado — requiere: (1) un certificado .p12 real emitido
        por el ATV para este taller, y (2) poder probar la firma contra el
        sandbox de Hacienda para validar que el XML resultante es válido.
        Librerías candidatas: signxml / xmlsig + cryptography (lectura del
        .p12) — evaluar cuando haya un certificado real para probar contra.
        """
        raise NotImplementedError(
            "Firma XAdES-BES no implementada: falta certificado .p12 real del taller. "
            "Ver docstring de ProveedorHaciendaDirecto._firmar_xml."
        )

    def _enviar_comprobante(self, clave: str, xml_firmado: bytes, token: str, config) -> ResultadoEmision:
        import base64

        url = HACIENDA_URLS[config.entorno]["recepcion"]
        payload = {
            "clave": clave,
            "fecha": datetime.now(dt_timezone.utc).isoformat(),
            "emisor": {"tipoIdentificacion": "02", "numeroIdentificacion": self._cedula(config)},
            "comprobanteXml": base64.b64encode(xml_firmado).decode("ascii"),
        }
        try:
            resp = requests.post(
                url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30
            )
        except requests.RequestException as exc:
            raise ErrorTransitorioFacturacionElectronica(f"No se pudo contactar la API de recepción: {exc}") from exc

        if resp.status_code >= 500:
            raise ErrorTransitorioFacturacionElectronica(f"API de recepción respondió {resp.status_code}")
        if resp.status_code not in (200, 201, 202):
            raise ProveedorFacturacionElectronicaError(
                f"Hacienda rechazó el comprobante ({resp.status_code}): {resp.text[:300]}"
            )

        return ResultadoEmision(
            proveedor="hacienda_directo",
            clave_numerica=clave,
            consecutivo=clave[19:39],
            estado="enviada",
            mensaje="Recibido por Hacienda, pendiente de resolución (consultar estado luego).",
        )

    @staticmethod
    def _cedula(config) -> str:
        return "".join(ch for ch in (config.taller.identificacion_fiscal or "") if ch.isdigit())
