from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("rol", Usuario.Rol.JURADO)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("rol", Usuario.Rol.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("debe_cambiar_password", False)
        return self._crear(email, password, **extra)


class Departamento(models.TextChoices):
    """Departamentos académicos permitidos (lista cerrada para estandarizar)."""

    SISTEMAS = "Sistemas", "Sistemas"
    CIVIL = "Ingeniería Civil", "Ingeniería Civil"
    ELECTRONICA = "Electrónica", "Electrónica"


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        JURADO = "JURADO", "Jurado"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("correo institucional", unique=True)
    nombre_completo = models.CharField(max_length=200)
    # Opcional solo para el administrador; para un JURADO lo exige el servicio de docentes.
    cedula = models.CharField(max_length=20, unique=True, null=True, blank=True)
    # Obligatorio para un JURADO (lo exige el serializer); vacío para el administrador.
    departamento = models.CharField(max_length=200, blank=True, choices=Departamento.choices)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.JURADO)
    debe_cambiar_password = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        ordering = ["nombre_completo"]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.cedula is not None:
            self.cedula = self.cedula.strip() or None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_completo} <{self.email}>"
