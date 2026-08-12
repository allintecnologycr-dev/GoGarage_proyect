from decimal import Decimal

from django.db import transaction

from rest_framework import serializers

from apps.ordenes.models import Cotizacion, OrdenTrabajo

from .models import ConfiguracionFacturacionElectronica, DetalleFactura, Factura, Pago


class DetalleFacturaSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleFactura
        fields = ["id", "factura", "descripcion", "cantidad", "precio_unitario", "subtotal"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        taller = getattr(request, "taller", None)
        if taller is not None:
            self.fields["factura"].queryset = Factura.objects.filter(taller=taller)


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ["id", "factura", "monto", "metodo", "fecha", "referencia"]
        read_only_fields = ["id", "fecha"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        taller = getattr(request, "taller", None)
        if taller is not None:
            self.fields["factura"].queryset = Factura.objects.filter(taller=taller)


class FacturaSerializer(serializers.ModelSerializer):
    detalles = DetalleFacturaSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    class Meta:
        model = Factura
        fields = [
            "id", "cliente", "cliente_nombre", "orden", "cotizacion", "numero", "fecha",
            "subtotal", "impuestos", "total", "estado",
            "proveedor_fe", "clave_numerica", "consecutivo", "estado_hacienda",
            "mensaje_hacienda", "xml_url", "pdf_url", "fecha_emision_fe",
            "detalles", "pagos",
        ]
        # Los campos de facturación electrónica los completa
        # emitir_factura_electronica (Celery), nunca el cliente de la API.
        read_only_fields = [
            "id", "fecha", "proveedor_fe", "clave_numerica", "consecutivo", "estado_hacienda",
            "mensaje_hacienda", "xml_url", "pdf_url", "fecha_emision_fe",
        ]


class ConfiguracionFacturacionElectronicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionFacturacionElectronica
        fields = [
            "id", "taller", "proveedor", "entorno", "usuario_atv", "contrasena_atv",
            "client_id_atv", "certificado_p12_path", "certificado_p12_password",
        ]
        read_only_fields = ["id", "taller"]
        extra_kwargs = {
            "contrasena_atv": {"write_only": True},
            "certificado_p12_password": {"write_only": True},
        }


class GenerarFacturaSerializer(serializers.Serializer):
    """
    Cierra una orden y genera su factura (ver docs/ARQUITECTURA.md sección
    2.4): si la orden tiene una Cotizacion aceptada, copia sus ítems;
    si no, arma los detalles desde ServicioOrden + RepuestoUsado. Al final
    encola la emisión electrónica en Celery.
    """

    orden = serializers.PrimaryKeyRelatedField(queryset=OrdenTrabajo.objects.all())

    def validate_orden(self, value):
        taller = self.context["request"].taller
        if value.taller_id != taller.id:
            raise serializers.ValidationError("La orden no pertenece a este taller.")
        if Factura.objects.filter(orden=value).exclude(estado=Factura.Estado.ANULADA).exists():
            raise serializers.ValidationError("Esta orden ya tiene una factura activa.")
        return value

    def create(self, validated_data):
        taller = self.context["request"].taller
        orden = validated_data["orden"]

        with transaction.atomic():
            # select_for_update evita que dos cierres simultáneos del mismo
            # taller generen el mismo número de factura.
            ultima = (
                Factura.objects.select_for_update().filter(taller=taller).order_by("-id").first()
            )
            siguiente = int(ultima.numero) + 1 if ultima and ultima.numero.isdigit() else 1
            numero = f"{siguiente:010d}"

            cotizacion_aceptada = orden.cotizaciones.filter(estado=Cotizacion.Estado.ACEPTADA).order_by("-fecha_creacion").first()

            factura = Factura.objects.create(
                taller=taller,
                cliente=orden.cliente,
                orden=orden,
                cotizacion=cotizacion_aceptada,
                numero=numero,
                impuestos=Decimal("0"),
            )

            if cotizacion_aceptada:
                for item in cotizacion_aceptada.detalles.all():
                    DetalleFactura.objects.create(
                        factura=factura, descripcion=item.descripcion,
                        cantidad=item.cantidad, precio_unitario=item.precio_unitario,
                    )
                factura.impuestos = cotizacion_aceptada.impuestos
            else:
                for servicio in orden.servicios.all():
                    DetalleFactura.objects.create(
                        factura=factura, descripcion=servicio.descripcion,
                        cantidad=1, precio_unitario=servicio.costo,
                    )
                for repuesto in orden.repuestos_usados.select_related("repuesto").all():
                    DetalleFactura.objects.create(
                        factura=factura, descripcion=str(repuesto.repuesto),
                        cantidad=repuesto.cantidad, precio_unitario=repuesto.costo_unitario,
                    )

            # El signal de DetalleFactura ya recalculó `subtotal` en la BD
            # (con impuestos=0 en ese momento); ahora que se conoce el
            # impuesto real, hay que refrescar `subtotal` y recomputar
            # `total` a mano — el signal no vuelve a correr acá porque no
            # se crea/borra ningún DetalleFactura en este paso.
            factura.refresh_from_db(fields=["subtotal"])
            factura.total = factura.subtotal + factura.impuestos
            factura.save(update_fields=["impuestos", "total"])

            if orden.estado not in (OrdenTrabajo.Estado.ENTREGADO, OrdenTrabajo.Estado.CANCELADO):
                orden.estado = OrdenTrabajo.Estado.ENTREGADO
                if not orden.fecha_entrega_real:
                    from django.utils import timezone
                    orden.fecha_entrega_real = timezone.now()
                orden.save(update_fields=["estado", "fecha_entrega_real"])

        factura.refresh_from_db()
        return factura
