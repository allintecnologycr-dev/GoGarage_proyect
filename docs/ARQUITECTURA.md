# GoGarage — Arquitectura y Modelo de Datos

Plataforma SaaS de gestión para talleres mecánicos y car services.
Versión: 0.2 · Fecha: 2026-08-11 (actualizado: foco de MVP de validación)

## 1. Resumen

GoGarage es un SaaS multi-tenant donde cada **taller** (cliente del SaaS) gestiona sus propios clientes finales, vehículos, órdenes de trabajo, citas, inventario y facturación, todo dentro de una única instalación compartida. El backend expone una API REST (Django REST Framework) que será consumida tanto por un frontend web propio (React/Next u similar) como, potencialmente, por una app móvil — por eso la API se diseña "headless" desde el día uno, con Django Admin como panel operativo/soporte interno, no como interfaz principal del usuario final.

## 2. MVP de validación (foco inicial)

Para validar la idea sin sobrecargar el desarrollo, el primer recorte funcional del producto **no** es "todo el sistema de gestión" sino un flujo delgado de punta a punta que un taller real puede usar desde el día uno. Este MVP reordena las prioridades del roadmap (ver sección 10) y se apoya en el modelo de datos ya definido (sección 5), añadiendo solo lo estrictamente necesario.

### 2.1 Recepción y diagnóstico
Apertura de orden por placa: el flujo de recepción busca la `Vehiculo` por `placa` dentro del taller (o la crea junto con su `Cliente` si es la primera visita) y genera la `OrdenTrabajo` en un paso, pensado para completarse desde el celular en el momento en que el carro entra al taller. Se agrega **recepción fotográfica**: el mecánico/recepción sube fotos del vehículo (estado de ingreso, daños, avances, entrega) directamente desde la cámara del celular. Vive en `apps.ordenes` como un nuevo modelo `EvidenciaFoto` asociado a la orden (ver 5.3).

### 2.2 Cotización rápida
Desde la orden (ya con diagnóstico), se arma un presupuesto (`Cotizacion`) con ítems de mano de obra/repuestos y se genera un **link público** de solo lectura (token no adivinable, sin login) que el asesor comparte al cliente con un botón "Enviar por WhatsApp" (deep link `https://wa.me/<telefono>?text=...`, sin necesidad de integrar la API de WhatsApp Business en esta etapa). El cliente puede aceptar o rechazar la cotización desde ese mismo link. Vive en `apps.ordenes` (ver 5.3), con una vista pública en la nueva app `apps.publico` (ver 5.4 y 6.4).

### 2.3 Estado del vehículo (landing pública)
Página pública accesible sin login mediante un link único por orden (mismo mecanismo de token que la cotización, **no** se expone buscando por placa directamente — ver nota de seguridad en 8) donde el cliente final ve el estado actual de su vehículo (recibido → diagnóstico → reparación → listo → entregado), las fotos relevantes, y un botón de contacto por WhatsApp — el objetivo es reducir llamadas al taller preguntando "¿cómo va mi carro?". Reutiliza `OrdenTrabajo.token_seguimiento` y vive en `apps.publico`.

### 2.4 Emisión de factura electrónica
Al cerrar la orden (o al aceptar la cotización y completarse el trabajo), se emite una factura electrónica **mediante integración con un proveedor de facturación API externo** en vez de construir la infraestructura contable/fiscal desde cero (firma XML, clave numérica, envío a Hacienda, contingencia, etc.). El backend define una interfaz de adaptador (`ProveedorFacturacionElectronica`) para no acoplarse a un proveedor específico — ver 5.5 y 8.

### 2.5 Qué queda fuera del MVP de validación
Inventario con control de stock fino, multi-taller avanzado (más de un taller por cuenta), reportes, recordatorios automáticos por Celery beat, y el frontend React completo quedan para después de validar el flujo core (recepción → cotización → seguimiento → factura). El scaffold ya entregado los deja modelados para no rehacer trabajo, pero no son el foco de las próximas iteraciones (ver roadmap, sección 10).

## 3. Stack tecnológico

| Capa | Tecnología | Rol |
|---|---|---|
| Framework web | Django | Base de la aplicación |
| API | Django REST Framework (DRF) | Endpoints REST para frontend/app |
| Autenticación API | djangorestframework-simplejwt | Tokens JWT (access/refresh) para clientes separados del backend |
| Admin | Django Admin | Panel interno para soporte, carga de datos, operaciones puntuales |
| ORM / migraciones | Django ORM | Persistencia y migraciones nativas |
| Base de datos | PostgreSQL (gestionado en Supabase en producción; Postgres local o contenedor en desarrollo) | Almacenamiento principal |
| Almacenamiento de archivos | Supabase Storage (S3-compatible) vía `django-storages` | Fotos de `EvidenciaFoto`; evita depender del disco local del servidor, que no escala ni persiste bien en despliegues sin estado |
| Servidor de aplicación | Gunicorn (WSGI) — Uvicorn/Uvicorn workers si se requiere ASGI para partes async | Servir la app en producción |
| Tareas asíncronas | Celery + Redis | Recordatorios de citas, notificaciones, generación de reportes, envío de correos, llamadas asíncronas al proveedor de facturación electrónica |
| CORS | django-cors-headers | Permitir que el frontend separado consuma la API |
| Mensajería al cliente (MVP) | Deep link `wa.me` (sin API de pago) | Compartir cotización y link de estado por WhatsApp; upgrade futuro a WhatsApp Business API (ej. Twilio/360dialog) si se necesita enviar mensajes automáticos salientes |
| Facturación electrónica | Integración vía API con un proveedor local autorizado (ej. Facturele, Konta, Alegra u otro con soporte para Costa Rica) | Emisión de comprobantes fiscalmente válidos sin construir la infraestructura de firma/envío a Hacienda internamente |

**Nota sobre Supabase:** ya existe `supabase.txt` en el repo con credenciales del proyecto. Estas credenciales **no deben commitearse a git**; deben moverse a variables de entorno (`.env`, fuera de control de versiones) y usarse solo para obtener el `DATABASE_URL` de Postgres. Se recomienda además rotar esa contraseña una vez migrada a un gestor de secretos, ya que quedó expuesta en el historial de git. Usar Supabase también para Storage (fotos) simplifica el stack: una sola cuenta/proveedor para base de datos y archivos.

## 4. Estrategia multi-tenant: esquema compartido + `tenant_id`

Se usa una única base de datos y un único esquema. Todas las tablas de negocio (clientes, vehículos, órdenes, citas, inventario, facturas, cotizaciones, evidencias) incluyen una FK obligatoria a `Taller` (el tenant). Ventajas para esta etapa del producto: migraciones simples (una sola vez para todos los tenants), fácil de operar sobre Supabase administrado, y consultas cross-tenant sencillas para analítica interna del SaaS.

Mecanismo de aislamiento:

- Un `TenantModel` abstracto añade `taller = models.ForeignKey("core.Taller", on_delete=models.CASCADE)` a todo modelo de negocio.
- Una permission class de DRF (`TienerTallerActivo`) resuelve el taller activo a partir del usuario ya autenticado por JWT (cada `Usuario` pertenece a uno o más `Taller` vía `Membresia`) y lo deja disponible en `request.taller`/`request.membresia`. Se implementa como permission class y no como middleware de Django, porque la autenticación JWT de DRF ocurre dentro de `dispatch()`, después del middleware — en middleware `request.user` aún no reflejaría al usuario del token.
- Un `TenantViewSet` base filtra automáticamente por `request.taller` en los `ViewSet` de DRF (`get_queryset()`/`perform_create()` comunes), de modo que ningún endpoint pueda filtrar accidentalmente datos de otro taller.
- Índices compuestos `(taller_id, ...)` en los campos más consultados (placa de vehículo, estado de orden, fecha de cita) para performance.
- **Excepción deliberada:** los endpoints públicos del MVP (cotización y estado de vehículo, sección 6.4) no pasan por este mecanismo porque no hay usuario autenticado — se resuelven por token único (ver sección 8), y ese token ya implica pertenencia a un taller y una orden concretos.

Si en el futuro un taller grande requiere aislamiento más fuerte (compliance, tamaño de datos), se puede migrar ese tenant puntual a un esquema separado sin rediseñar el resto — la mixin ya aísla lógicamente los datos.

## 5. Entidades principales

### 5.1 Núcleo / cuentas
- **Taller** — nombre, slug, plan de suscripción, datos fiscales, fecha de alta, estado (activo/suspendido).
- **Usuario** (custom user model) — email como login, nombre, teléfono, `is_active`.
- **Membresia** — Usuario ↔ Taller con `rol` (admin_taller, recepcion, mecanico, contable) y `activo`. Permite que un usuario pertenezca a más de un taller (ej. dueño de cadena de talleres) y que los permisos se evalúen por combinación usuario+taller.

### 5.2 Clientes y vehículos
- **Cliente** — taller (FK), nombre/razón social, identificación, teléfono, email, dirección.
- **Vehiculo** — taller (FK), cliente (FK), placa, marca, modelo, año, VIN, kilometraje actual, notas.

### 5.3 Operación (incluye lo nuevo del MVP)
- **OrdenTrabajo** — taller, vehiculo, cliente, mecánico asignado (Usuario), fecha de ingreso, fecha estimada de entrega, estado (recibido, en_diagnostico, en_reparacion, esperando_repuesto, listo, entregado, cancelado), kilometraje de ingreso, diagnóstico, observaciones, **`token_seguimiento`** (UUID único, generado al crear la orden — es la base del link público de estado, sección 2.3).
- **ServicioOrden** — orden (FK), descripción del servicio/mano de obra, horas, costo.
- **RepuestoUsado** — orden (FK), repuesto (FK a Repuesto), cantidad, costo unitario al momento de uso.
- **EvidenciaFoto** *(nuevo)* — taller, orden (FK), imagen (archivo en Supabase Storage), tipo (`ingreso`, `diagnostico`, `reparacion`, `entrega`), descripción, subida_por (Usuario), fecha. Se muestra tanto en el panel interno como en la landing pública de estado.
- **Cotizacion** *(nuevo)* — taller, orden (FK), cliente, `token_publico` (UUID único para el link de WhatsApp), subtotal, impuestos, total, estado (`borrador`, `enviada`, `aceptada`, `rechazada`, `vencida`), fecha_creacion, fecha_expiracion, fecha_respuesta.
- **DetalleCotizacion** *(nuevo)* — cotizacion (FK), descripción, cantidad, precio_unitario (misma forma que `DetalleFactura`; al aceptarse la cotización estos ítems pueden precargar la factura).
- **Cita** — taller, cliente, vehiculo (opcional si aún no está registrado), fecha/hora, motivo, estado (pendiente, confirmada, cumplida, cancelada, no_show), orden_generada (FK opcional una vez que la cita se convierte en orden).

### 5.4 Inventario
- **Repuesto** — taller, código/SKU, nombre, categoría, unidad de medida, costo promedio, precio de venta, stock actual, stock mínimo.
- **MovimientoInventario** — repuesto (FK), tipo (entrada, salida, ajuste), cantidad, referencia (orden relacionada si aplica), fecha, usuario responsable.

### 5.5 Facturación (incluye factura electrónica)
- **Factura** — taller, cliente, orden (FK opcional, una factura puede agrupar varias órdenes), cotizacion (FK opcional, si nació de una cotización aceptada), número, fecha, subtotal, impuestos, total, estado (pendiente, pagada, anulada), y campos de **facturación electrónica**: `proveedor_fe` (qué integración se usó), `clave_numerica`/`consecutivo` (identificador fiscal que devuelve el proveedor), `estado_hacienda` (pendiente, aceptado, rechazado), `xml_url`, `pdf_url`.
- **DetalleFactura** — factura (FK), descripción, cantidad, precio unitario, subtotal (se puede generar automáticamente desde ServicioOrden + RepuestoUsado, o copiarse desde una `Cotizacion` aceptada).
- **Pago** — factura (FK), monto, método (efectivo, tarjeta, transferencia, sinpe), fecha, referencia.
- **Integración de facturación electrónica:** se define una interfaz `ProveedorFacturacionElectronica` (método `emitir(factura) -> resultado`) implementada por un adaptador concreto (ej. `FacturaProveedorX`) configurable por variable de entorno. Esto permite cambiar de proveedor sin tocar el resto del sistema, y correr la emisión como tarea Celery (la respuesta del proveedor puede tardar o requerir reintentos).

### 5.6 Diagrama de relaciones (simplificado)

```
Taller 1---N Membresia N---1 Usuario
Taller 1---N Cliente 1---N Vehiculo
Taller 1---N OrdenTrabajo N---1 Vehiculo
OrdenTrabajo 1---N ServicioOrden
OrdenTrabajo 1---N RepuestoUsado N---1 Repuesto
OrdenTrabajo 1---N EvidenciaFoto
OrdenTrabajo 1---N Cotizacion 1---N DetalleCotizacion
Taller 1---N Cita N---1 (Cliente, Vehiculo opcional)
Taller 1---N Repuesto 1---N MovimientoInventario
Taller 1---N Factura N---1 Cliente
Factura N---1 Cotizacion (opcional)
Factura 1---N DetalleFactura
Factura 1---N Pago
```

## 6. Diseño de la API (DRF)

- Prefijo versionado: `/api/v1/...`.
- Autenticación: JWT (`simplejwt`) — `POST /api/v1/auth/token/` y `/token/refresh/`. El frontend separado guarda el access/refresh token y los envía como `Authorization: Bearer <token>`.
- CORS habilitado (`django-cors-headers`) solo para los orígenes del/los frontend(s) configurados por variable de entorno.
- Todos los endpoints de negocio requieren `Membresia` activa; el taller activo se resuelve por header (`X-Taller-Id`) o por el único taller del usuario si no tiene ambigüedad, y se valida contra las membresías del usuario autenticado — nunca se confía en un tenant_id enviado libremente sin verificar pertenencia.
- Paginación por defecto (`PageNumberPagination`), filtros (`django-filter`) por estado, fecha, cliente, vehículo, y búsqueda por placa/nombre.
- Permisos por rol a nivel de `ViewSet` (ej. solo `admin_taller`/`contable` puede anular facturas; `mecanico` puede actualizar estado de su orden pero no eliminarla).

### 6.4 Endpoints públicos (sin autenticación) — nuevos para el MVP
Viven en una app nueva y aislada, `apps.publico`, con `permission_classes = [AllowAny]` y **sin** pasar por `TenantViewSet` (se resuelven directo por token, sección 8):

- `GET /api/v1/public/ordenes/<token_seguimiento>/` — estado actual de la orden, línea de tiempo, fotos públicas. Solo lectura.
- `GET /api/v1/public/cotizaciones/<token_publico>/` — detalle de la cotización (ítems, total, vigencia).
- `POST /api/v1/public/cotizaciones/<token_publico>/aceptar/` y `.../rechazar/` — el cliente responde desde el link; cambia `Cotizacion.estado` y dispara notificación interna (Celery) al taller.

Para el MVP, estas dos páginas (estado y cotización) pueden servirse como vistas Django simples (server-rendered) en vez de esperar al frontend React completo — reduce el tiempo a validar el flujo end-to-end; migran al frontend separado cuando exista.

## 7. Celery + Redis — casos de uso iniciales

- Recordatorio de cita (email/SMS) N horas antes.
- Notificación al cliente cuando su orden cambia de estado (ej. "listo para retirar").
- Notificación interna al taller cuando el cliente acepta/rechaza una cotización desde el link público.
- Llamada al proveedor de facturación electrónica al cerrar una orden/factura, con reintentos si el proveedor no responde de inmediato.
- Generación de reportes pesados (ventas por período, rotación de inventario) en background con resultado descargable.
- Envío de factura por correo al cliente.
- Tareas periódicas (Celery beat): alertas de stock mínimo, recordatorio de citas del día siguiente, vencimiento automático de cotizaciones no respondidas.

## 8. Seguridad y buenas prácticas

- Nunca commitear `.env` ni credenciales; usar `.env.example` como plantilla. Se recomienda quitar `supabase.txt` del control de versiones y rotar la contraseña ahí expuesta.
- Aislamiento de tenant validado en la permission class y en cada queryset (defensa en profundidad).
- HTTPS obligatorio en producción; `SECURE_*` settings de Django activados.
- Rate limiting básico en endpoints de autenticación.
- **Tokens públicos no adivinables:** `OrdenTrabajo.token_seguimiento` y `Cotizacion.token_publico` son UUIDv4, nunca la `placa` ni un ID incremental — una placa es públicamente conocida/observable y un ID autoincremental es enumerable, así que ninguno de los dos es apto como credencial de acceso a datos del cliente. El flujo interno (recepción) es el que busca por placa; el link que sale del taller hacia el cliente siempre lleva el token.
- Rate limiting específico en los endpoints públicos (`apps.publico`) para evitar fuerza bruta sobre los tokens, y los serializers públicos exponen solo los campos necesarios (nunca datos de otros clientes, costos internos de repuestos, notas internas, etc.).
- Los endpoints públicos no filtran por `request.taller` (no hay sesión de taller): filtran directamente `WHERE token = <token>`, y ese registro ya pertenece a un taller y un cliente determinados — no hay forma de listar ni de moverse lateralmente a otros registros.

## 9. Estructura de proyecto propuesta

```
gogarage/
├── config/                # settings, urls, wsgi/asgi, celery.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
├── apps/
│   ├── core/               # Taller, Usuario, Membresia, TenantModel, permisos de tenant
│   ├── clientes/            # Cliente, Vehiculo
│   ├── ordenes/             # OrdenTrabajo, ServicioOrden, RepuestoUsado, EvidenciaFoto,
│   │                        # Cotizacion, DetalleCotizacion, Cita
│   ├── inventario/          # Repuesto, MovimientoInventario
│   ├── facturacion/         # Factura, DetalleFactura, Pago, adaptador de facturación electrónica
│   └── publico/             # (nuevo) vistas sin autenticación por token: estado de orden y cotización
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── docker-compose.yml       # postgres local + redis para desarrollo
└── .env.example
```

## 10. Roadmap sugerido

El roadmap se reordena para priorizar el **MVP de validación** (sección 2) antes que completar cada módulo a fondo.

1. **Fase 0 (ya entregada):** scaffold del backend, modelos base, admin, API CRUD mínima, auth JWT, aislamiento multi-tenant.
2. **Fase 1 — MVP de validación:**
   1. Recepción y diagnóstico: alta rápida de orden por placa + `EvidenciaFoto` con subida de imágenes desde el celular (Supabase Storage).
   2. Cotización rápida: `Cotizacion`/`DetalleCotizacion` + generación de link público + botón "enviar por WhatsApp" (`wa.me`).
   3. Landing pública de estado del vehículo por `token_seguimiento` (`apps.publico`).
   4. Emisión de factura electrónica al cerrar la orden, vía adaptador a un proveedor local.
3. **Fase 2:** citas y flujo completo de orden de trabajo (recepción → diagnóstico → reparación → entrega) más allá de lo mínimo del MVP.
4. **Fase 3:** inventario con movimientos automáticos al usar repuestos en una orden.
5. **Fase 4:** facturación avanzada (pagos parciales, notas de crédito) y reportes; tareas Celery beat completas (recordatorios, alertas de stock).
6. **Fase 5:** frontend web propio conectado a la API (hoy las páginas públicas se sirven server-rendered); pulido de permisos por rol y multi-taller.
