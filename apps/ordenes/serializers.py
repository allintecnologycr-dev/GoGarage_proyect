from django.db import transaction

from rest_framework import serializers

from apps.clientes.models import Cliente, Vehiculo
from apps.core.models import Membresia, Usuario

from .models import Cita, EvidenciaFoto, OrdenTrabajo, RepuestoUsado, ServicioOrden

TAMANO_MAXIMO_FOTO_BYTES = 15 * 1024 * 1024


class ServicioOrdenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicioOrden
        fields = ["id", "orden", "descripcion", "horas", "costo"]
        read_only_fields = ["id"]


class RepuestoUsadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepuestoUsado
        fields = ["id", "orden", "repuesto", "cantidad", "costo_unitario"]
        read_only_fields = ["id"]


class EvidenciaFotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenciaFoto
        fields = ["id", "orden", "imagen", "tipo", "descripcion", "subida_por", "created_at"]
        read_only_fields = ["id", "subida_por", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El queryset del FK `orden` se restringe al taller activo para que
        # no se pueda asociar una foto a la orden de otro taller (ver
        # docs/ARQUITECTURA.md sección 8, aislamiento de tenant en profundidad).
        request = self.context.get("request")
        taller = getattr(request, "taller", None)
        if taller is not None:
            self.fields["orden"].queryset = OrdenTrabajo.objects.filter(taller=taller)

    def validate_imagen(self, value):
        if value.size > TAMANO_MAXIMO_FOTO_BYTES:
            raise serializers.ValidationError("La imagen no puede superar 15MB.")
        return value


class OrdenTrabajoSerializer(serializers.ModelSerializer):
    servicios = ServicioOrdenSerializer(many=True, read_only=True)
    repuestos_usados = RepuestoUsadoSerializer(many=True, read_only=True)
    evidencias_foto = EvidenciaFotoSerializer(many=True, read_only=True)
    vehiculo_placa = serializers.CharField(source="vehiculo.placa", read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    class Meta:
        model = OrdenTrabajo
        fields = [
            "id", "vehiculo", "vehiculo_placa", "cliente", "cliente_nombre", "mecanico", "estado",
            "fecha_ingreso", "fecha_estimada_entrega", "fecha_entrega_real",
            "kilometraje_ingreso", "diagnostico", "observaciones",
            "servicios", "repuestos_usados", "evidencias_foto", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "fecha_ingreso", "created_at", "updated_at"]


class CitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = [
            "id", "cliente", "vehiculo", "fecha_hora", "motivo", "estado",
            "orden_generada", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RecepcionRapidaSerializer(serializers.Serializer):
    """
    Alta rápida de orden por placa (apertura de orden en un solo paso desde
    el celular en el momento en que el carro entra al taller): busca el
    `Vehiculo` por `placa` dentro del taller activo, o lo crea junto con su
    `Cliente` si es la primera visita, y genera la `OrdenTrabajo`.
    """

    placa = serializers.CharField(max_length=20)
    marca = serializers.CharField(max_length=50, required=False, allow_blank=True)
    modelo = serializers.CharField(max_length=50, required=False, allow_blank=True)
    anio = serializers.IntegerField(required=False, allow_null=True)
    vin = serializers.CharField(max_length=50, required=False, allow_blank=True)
    kilometraje_ingreso = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    diagnostico = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    mecanico = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), required=False, allow_null=True
    )
    cliente_nombre = serializers.CharField(max_length=150, required=False, allow_blank=True)
    cliente_telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cliente_identificacion = serializers.CharField(max_length=50, required=False, allow_blank=True)
    cliente_email = serializers.EmailField(required=False, allow_blank=True)

    def validate_placa(self, value):
        placa = value.strip().upper()
        if not placa:
            raise serializers.ValidationError("La placa no puede estar vacía.")
        return placa

    def validate_mecanico(self, value):
        taller = self.context["request"].taller
        if not Membresia.objects.filter(usuario=value, taller=taller, activo=True).exists():
            raise serializers.ValidationError("El mecánico no tiene una membresía activa en este taller.")
        return value

    def validate(self, attrs):
        taller = self.context["request"].taller
        vehiculo_existe = Vehiculo.objects.filter(taller=taller, placa=attrs["placa"]).exists()
        if not vehiculo_existe and not attrs.get("cliente_nombre"):
            raise serializers.ValidationError(
                {"cliente_nombre": "La placa no está registrada: se necesita el nombre del cliente para darlo de alta."}
            )
        return attrs

    def create(self, validated_data):
        taller = self.context["request"].taller
        placa = validated_data["placa"]

        with transaction.atomic():
            vehiculo = (
                Vehiculo.objects.select_related("cliente").filter(taller=taller, placa=placa).first()
            )
            vehiculo_nuevo = vehiculo is None
            if vehiculo is None:
                cliente = Cliente.objects.create(
                    taller=taller,
                    nombre=validated_data["cliente_nombre"],
                    telefono=validated_data.get("cliente_telefono", ""),
                    identificacion=validated_data.get("cliente_identificacion", ""),
                    email=validated_data.get("cliente_email", ""),
                )
                vehiculo = Vehiculo.objects.create(
                    taller=taller,
                    cliente=cliente,
                    placa=placa,
                    marca=validated_data.get("marca", ""),
                    modelo=validated_data.get("modelo", ""),
                    anio=validated_data.get("anio"),
                    vin=validated_data.get("vin", ""),
                )
            else:
                cliente = vehiculo.cliente

            orden = OrdenTrabajo.objects.create(
                taller=taller,
                vehiculo=vehiculo,
                cliente=cliente,
                mecanico=validated_data.get("mecanico"),
                kilometraje_ingreso=validated_data.get("kilometraje_ingreso"),
                diagnostico=validated_data.get("diagnostico", ""),
                observaciones=validated_data.get("observaciones", ""),
            )

        orden.vehiculo_nuevo = vehiculo_nuevo
        return orden
