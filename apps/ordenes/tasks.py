"""
Tareas Celery iniciales para el módulo de órdenes/citas (ver docs/ARQUITECTURA.md
sección "Celery + Redis"). Se registran automáticamente vía app.autodiscover_tasks().
"""

from celery import shared_task
from django.core.mail import send_mail


@shared_task
def enviar_recordatorio_cita(cita_id: int) -> str:
    from .models import Cita

    try:
        cita = Cita.objects.select_related("cliente", "taller").get(pk=cita_id)
    except Cita.DoesNotExist:
        return f"Cita {cita_id} no existe"

    if cita.cliente.email:
        send_mail(
            subject=f"Recordatorio de cita — {cita.taller.nombre}",
            message=(
                f"Hola {cita.cliente.nombre}, te recordamos tu cita el "
                f"{cita.fecha_hora:%d/%m/%Y %H:%M} en {cita.taller.nombre}."
            ),
            from_email=None,
            recipient_list=[cita.cliente.email],
        )
    return f"Recordatorio enviado para cita {cita_id}"


@shared_task
def notificar_orden_lista(orden_id: int) -> str:
    from .models import OrdenTrabajo

    try:
        orden = OrdenTrabajo.objects.select_related("cliente", "vehiculo", "taller").get(pk=orden_id)
    except OrdenTrabajo.DoesNotExist:
        return f"Orden {orden_id} no existe"

    if orden.cliente.email:
        send_mail(
            subject=f"Tu vehículo está listo — {orden.taller.nombre}",
            message=f"Hola {orden.cliente.nombre}, tu vehículo {orden.vehiculo.placa} ya está listo para retirar.",
            from_email=None,
            recipient_list=[orden.cliente.email],
        )
    return f"Notificación enviada para orden {orden_id}"
