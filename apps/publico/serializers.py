from urllib.parse import quote

from rest_framework import serializers

from apps.ordenes.models import Cotizacion, DetalleCotizacion, EvidenciaFoto, OrdenTrabajo

_PASOS_TIMELINE = [
    (OrdenTrabajo.Estado.RECIBIDO, "Recibido"),
    (OrdenTrabajo.Estado.EN_DIAGNOSTICO, "En diagnóstico"),
    (OrdenTrabajo.Estado.EN_REPARACION, "En reparación"),
    (OrdenTrabajo.Estado.LISTO, "Listo para retirar"),
    (OrdenTrabajo.Estado.ENTREGADO, "Entregado"),
]

# "Esperando repuesto" es una pausa dentro de "En reparación": se muestra
# como si fuera ese mismo paso del timeline, no agrega una columna aparte.
_EQUIVALENCIA_PASO = {
    OrdenTrabajo.Estado.ESPERANDO_REPUESTO: OrdenTrabajo.Estado.EN_REPARACION,
}


def _construir_timeline(estado):
    estado_efectivo = _EQUIVALENCIA_PASO.get(estado, estado)
    try:
        indice_actual = [paso for paso, _ in _PASOS_TIMELINE].index(estado_efectivo)
    except ValueError:
        indice_actual = -1  # cancelado: fuera del happy path, no resalta ningún paso

    ultimo_indice = len(_PASOS_TIMELINE) - 1
    pasos = []
    for i, (paso, etiqueta) in enumerate(_PASOS_TIMELINE):
        if indice_actual == -1:
            estado_paso = "pendiente"
        elif i < indice_actual:
            estado_paso = "completado"
        elif i == indice_actual:
            # El último paso (entregado) es un hito terminado, no "en curso"
            # como los intermedios — se muestra con el mismo check que los
            # anteriores en vez de resaltado como "actual".
            estado_paso = "completado" if i == ultimo_indice else "actual"
        else:
            estado_paso = "pendiente"
        pasos.append({"clave": paso, "etiqueta": etiqueta, "estado": estado_paso})
    return pasos


class DetalleCotizacionPublicaSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleCotizacion
        fields = ["descripcion", "cantidad", "precio_unitario", "subtotal"]


class CotizacionPublicaSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para el link público de una cotización.
    Expone únicamente lo que el cliente final necesita ver — nunca costos
    internos, notas del taller, ni datos de otros clientes (ver
    docs/ARQUITECTURA.md sección 8).
    """

    taller_nombre = serializers.CharField(source="taller.nombre", read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)
    vehiculo = serializers.SerializerMethodField()
    detalles = DetalleCotizacionPublicaSerializer(many=True, read_only=True)
    vencida = serializers.BooleanField(read_only=True)
    respondible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            "taller_nombre", "cliente_nombre", "vehiculo",
            "subtotal", "impuestos", "total", "estado", "vencida", "respondible",
            "fecha_creacion", "fecha_expiracion", "fecha_respuesta", "detalles",
        ]

    def get_vehiculo(self, obj):
        vehiculo = obj.orden.vehiculo
        return f"{vehiculo.marca} {vehiculo.modelo} — {vehiculo.placa}".strip()


class EvidenciaFotoPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenciaFoto
        fields = ["imagen", "tipo", "descripcion", "created_at"]


class OrdenPublicaSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para el link de estado del vehículo (ver
    docs/ARQUITECTURA.md sección 2.3). No expone diagnóstico/observaciones
    internas del taller — solo estado, fotos y datos del vehículo.
    """

    taller_nombre = serializers.CharField(source="taller.nombre", read_only=True)
    vehiculo = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    cancelado = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    fotos = EvidenciaFotoPublicaSerializer(source="evidencias_foto", many=True, read_only=True)
    link_whatsapp_taller = serializers.SerializerMethodField()

    class Meta:
        model = OrdenTrabajo
        fields = [
            "taller_nombre", "vehiculo", "estado", "estado_display", "cancelado", "timeline",
            "fecha_ingreso", "fecha_estimada_entrega", "fecha_entrega_real", "fotos",
            "link_whatsapp_taller",
        ]

    def get_vehiculo(self, obj):
        vehiculo = obj.vehiculo
        return f"{vehiculo.marca} {vehiculo.modelo} — {vehiculo.placa}".strip()

    def get_cancelado(self, obj):
        return obj.estado == OrdenTrabajo.Estado.CANCELADO

    def get_timeline(self, obj):
        return _construir_timeline(obj.estado)

    def get_link_whatsapp_taller(self, obj):
        telefono = "".join(ch for ch in (obj.taller.telefono or "") if ch.isdigit())
        if not telefono:
            return None
        mensaje = f"Hola, quiero consultar sobre mi vehículo {obj.vehiculo.placa}."
        return f"https://wa.me/{telefono}?text={quote(mensaje)}"
