from rest_framework import serializers

from .models import MovimientoInventario, Repuesto


class RepuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repuesto
        fields = [
            "id", "sku", "nombre", "categoria", "unidad_medida",
            "costo_promedio", "precio_venta", "stock_actual", "stock_minimo",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = ["id", "repuesto", "tipo", "cantidad", "orden", "usuario", "fecha", "notas"]
        read_only_fields = ["id", "fecha"]

    def create(self, validated_data):
        """Actualiza el stock del repuesto de forma atómica al registrar el movimiento."""
        from django.db import transaction

        with transaction.atomic():
            movimiento = super().create(validated_data)
            repuesto = movimiento.repuesto
            delta = movimiento.cantidad if movimiento.tipo == MovimientoInventario.Tipo.ENTRADA else -movimiento.cantidad
            if movimiento.tipo == MovimientoInventario.Tipo.AJUSTE:
                delta = movimiento.cantidad
            repuesto.stock_actual = repuesto.stock_actual + delta
            repuesto.save(update_fields=["stock_actual"])
        return movimiento
