# GoGarage

Plataforma SaaS de gestión para talleres mecánicos y car services.

Ver [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) para el detalle de arquitectura, modelo de datos y decisiones (multi-tenant, API, Celery).

## Requisitos

- Python 3.11+
- Docker (para Postgres y Redis en desarrollo local) — o Supabase/Postgres accesible directamente.

## Puesta en marcha (desarrollo)

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt

cp .env.example .env             # Completar SECRET_KEY, DATABASE_URL, etc.
docker compose up -d             # Levanta Postgres y Redis locales

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

En otra terminal, para procesar tareas asíncronas (recordatorios, notificaciones):

```bash
celery -A config worker -l info
celery -A config beat -l info    # tareas periódicas (stock mínimo, recordatorios del día siguiente)
```

## Estructura

```
config/          # settings (base/dev/prod), urls, celery.py
apps/
  core/          # Taller, Usuario, Membresia, middleware multi-tenant, permisos
  clientes/      # Cliente, Vehículo
  ordenes/       # OrdenTrabajo, ServicioOrden, RepuestoUsado, Cita, tareas Celery
  inventario/    # Repuesto, MovimientoInventario
  facturacion/   # Factura, DetalleFactura, Pago
docs/            # documentación de arquitectura
```

## API

- Auth JWT: `POST /api/v1/auth/token/`, `POST /api/v1/auth/token/refresh/`
- Perfil del usuario autenticado: `GET /api/v1/me/`
- Recursos: `/api/v1/talleres/`, `/api/v1/clientes/`, `/api/v1/vehiculos/`, `/api/v1/ordenes/`, `/api/v1/citas/`, `/api/v1/repuestos/`, `/api/v1/movimientos-inventario/`, `/api/v1/facturas/`, etc.
- Todos los endpoints de negocio (excepto `/me/` y `/talleres/`) requieren que la request resuelva un taller activo. Si el usuario pertenece a más de un taller, enviar el header `X-Taller-Id: <id>`.
- Django Admin: `/admin/` (panel interno de soporte/operación).

## Notas de seguridad

`supabase.txt` contiene una contraseña de base de datos y **no debe estar en git**. Ya se agregó a `.gitignore`; se recomienda quitarlo del historial y rotar la contraseña, y mover la cadena de conexión real a `DATABASE_URL` en `.env` (nunca commiteado).
