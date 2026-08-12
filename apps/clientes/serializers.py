from rest_framework import serializers

from .models import Cliente, Vehiculo


class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = [
            "id", "cliente", "placa", "marca", "modelo", "anio", "vin",
            "kilometraje_actual", "notas", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClienteSerializer(serializers.ModelSerializer):
    vehiculos = VehiculoSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id", "nombre", "identificacion", "telefono", "email", "direccion",
            "vehiculos", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
