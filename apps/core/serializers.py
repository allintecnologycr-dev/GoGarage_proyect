from rest_framework import serializers

from .models import Membresia, Taller, Usuario


class TallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taller
        fields = ["id", "nombre", "slug", "identificacion_fiscal", "telefono", "direccion", "plan", "estado"]
        read_only_fields = ["id"]


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre", "telefono", "is_active"]
        read_only_fields = ["id", "is_active"]


class MembresiaSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)
    taller_nombre = serializers.CharField(source="taller.nombre", read_only=True)

    class Meta:
        model = Membresia
        fields = ["id", "usuario", "usuario_email", "taller", "taller_nombre", "rol", "activo"]
        read_only_fields = ["id"]


class MeSerializer(serializers.ModelSerializer):
    """Perfil del usuario autenticado + sus membresías, para que el frontend
    sepa a qué talleres pertenece y con qué rol."""

    membresias = MembresiaSerializer(many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre", "telefono", "membresias"]
