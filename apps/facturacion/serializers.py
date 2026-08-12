from rest_framework import serializers

from .models import DetalleFactura, Factura, Pago


class DetalleFacturaSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleFactura
        fields = ["id", "factura", "descripcion", "cantidad", "precio_unitario", "subtotal"]
        read_only_fields = ["id"]


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ["id", "factura", "monto", "metodo", "fecha", "referencia"]
        read_only_fields = ["id", "fecha"]


class FacturaSerializer(serializers.ModelSerializer):
    detalles = DetalleFacturaSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)

    class Meta:
        model = Factura
        fields = [
            "id", "cliente", "orden", "numero", "fecha", "subtotal",
            "impuestos", "total", "estado", "detalles", "pagos",
        ]
        read_only_fields = ["id", "fecha"]
