import datetime
from decimal import Decimal

import factory

from core.models import Usuario
from evaluaciones.models import (
    AreaConocimiento,
    Asignacion,
    Autor,
    EstadoProyecto,
    Evaluacion,
    Evento,
    Origen,
    Proyecto,
    Tipo,
)


class UsuarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"docente{n}@udenar.edu.co")
    nombre_completo = factory.Faker("name", locale="es_CO")
    cedula = factory.Sequence(lambda n: f"{10000000 + n}")
    departamento = "Sistemas"
    rol = Usuario.Rol.JURADO
    debe_cambiar_password = True

    @factory.post_generation
    def password(obj, create, valor, **kwargs):
        # Por defecto, la contraseña es la cédula (RN-06).
        obj.set_password(valor or obj.cedula or "Admin-Prueba-2026")
        if create:
            obj.save(update_fields=["password"])


class JuradoFactory(UsuarioFactory):
    pass


class AdminFactory(UsuarioFactory):
    rol = Usuario.Rol.ADMIN
    cedula = None
    debe_cambiar_password = False
    is_staff = True
    is_superuser = True


class EventoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evento

    nombre = factory.Sequence(lambda n: f"Encuentro de Semilleros {n}")
    fecha = datetime.date(2026, 10, 9)
    activo = False


class AreaFactory(factory.django.DjangoModelFactory):
    """Usa las áreas cargadas por la migración de datos."""

    class Meta:
        model = AreaConocimiento
        django_get_or_create = ("programa", "nombre")

    programa = "IS"
    nombre = "Ingeniería de software"


class ProyectoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proyecto

    evento = factory.SubFactory(EventoFactory)
    codigo = factory.Sequence(lambda n: f"P-{n:03d}")
    titulo = factory.Sequence(lambda n: f"Proyecto de prueba {n}")
    area = factory.SubFactory(AreaFactory)
    origen = Origen.SEMILLERO
    tipo = Tipo.INV
    estado = EstadoProyecto.EN_CURSO


class AutorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Autor

    proyecto = factory.SubFactory(ProyectoFactory)
    nombre_completo = factory.Faker("name", locale="es_CO")
    cedula = factory.Sequence(lambda n: f"{1080000000 + n}")
    orden = factory.Sequence(lambda n: n % 5 + 1)


class AsignacionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asignacion

    proyecto = factory.SubFactory(ProyectoFactory)
    docente = factory.SubFactory(JuradoFactory)


class EvaluacionFactory(factory.django.DjangoModelFactory):
    """Evaluación enviada mínima (sin detalles); suficiente para las reglas que dependen de que exista."""

    class Meta:
        model = Evaluacion

    asignacion = factory.SubFactory(AsignacionFactory)
    total = Decimal("80.00")
