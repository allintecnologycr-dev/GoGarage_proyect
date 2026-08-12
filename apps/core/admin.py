from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Membresia, Taller, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ["email"]
    list_display = ["email", "nombre", "is_active", "is_staff"]
    search_fields = ["email", "nombre"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre", "telefono")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nombre", "password1", "password2")}),
    )


class MembresiaInline(admin.TabularInline):
    model = Membresia
    extra = 0


@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = ["nombre", "slug", "plan", "estado", "created_at"]
    list_filter = ["plan", "estado"]
    search_fields = ["nombre", "slug"]
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [MembresiaInline]


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ["usuario", "taller", "rol", "activo"]
    list_filter = ["rol", "activo", "taller"]
    search_fields = ["usuario__email", "taller__nombre"]
