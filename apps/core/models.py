from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class TimestampedModel(models.Model):
    """Campos de auditoría comunes a todos los modelos del dominio."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Taller(TimestampedModel):
    """Un tenant del SaaS: un taller mecánico / car service."""

    class Plan(models.TextChoices):
        GRATIS = "gratis", "Gratis"
        BASICO = "basico", "Básico"
        PRO = "pro", "Pro"

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        SUSPENDIDO = "suspendido", "Suspendido"

    nombre = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    identificacion_fiscal = models.CharField(max_length=50, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.GRATIS)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class TenantModel(TimestampedModel):
    """
    Base abstracta para todo modelo de negocio: fija el aislamiento
    multi-tenant (esquema compartido + tenant_id) descrito en
    docs/ARQUITECTURA.md.
    """

    taller = models.ForeignKey(Taller, on_delete=models.CASCADE, related_name="+")

    class Meta:
        abstract = True


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un email")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuario del SaaS. Puede pertenecer a uno o más talleres vía Membresia."""

    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.nombre

    def get_short_name(self):
        return self.nombre


class Membresia(TimestampedModel):
    """Relación Usuario <-> Taller con un rol; habilita multi-taller por usuario."""

    class Rol(models.TextChoices):
        ADMIN_TALLER = "admin_taller", "Administrador de taller"
        RECEPCION = "recepcion", "Recepción"
        MECANICO = "mecanico", "Mecánico"
        CONTABLE = "contable", "Contable"

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="membresias")
    taller = models.ForeignKey(Taller, on_delete=models.CASCADE, related_name="membresias")
    rol = models.CharField(max_length=20, choices=Rol.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "taller"], name="unica_membresia_usuario_taller")
        ]

    def __str__(self):
        return f"{self.usuario} @ {self.taller} ({self.rol})"
