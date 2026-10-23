"""Restricciones de base de datos (fase 1) y catálogo de áreas."""

import datetime

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction

from core.models import Usuario
from evaluaciones.models import AreaConocimiento, Asignacion, Evento, Proyecto

from .factories import (
    AsignacionFactory,
    AutorFactory,
    EventoFactory,
    JuradoFactory,
    ProyectoFactory,
)

pytestmark = pytest.mark.django_db


def falla_integridad():
    """Contexto que espera un IntegrityError sin romper la transacción de la prueba."""

    class _Ctx:
        def __enter__(self):
            self.raises = pytest.raises(IntegrityError)
            self.raises.__enter__()
            self.atomic = transaction.atomic()
            self.atomic.__enter__()

        def __exit__(self, *exc):
            self.atomic.__exit__(*exc)
            return self.raises.__exit__(*exc)

    return _Ctx()


def test_no_faltan_migraciones():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


# RN-02
def test_solo_un_evento_activo():
    EventoFactory(activo=True)
    EventoFactory(activo=False)
    EventoFactory(activo=False)
    with falla_integridad():
        EventoFactory(activo=True)
    assert Evento.objects.filter(activo=True).count() == 1


# RN-13
def test_codigo_unico_dentro_del_evento():
    proyecto = ProyectoFactory(codigo="SI-01")
    with falla_integridad():
        ProyectoFactory(codigo="SI-01", evento=proyecto.evento)


def test_mismo_codigo_en_otro_evento_es_valido():
    ProyectoFactory(codigo="SI-01")
    ProyectoFactory(codigo="SI-01")
    assert Proyecto.objects.filter(codigo="SI-01").count() == 2


# RN-17
def test_trabajo_de_grado_no_puede_estar_en_propuesta():
    with falla_integridad():
        ProyectoFactory(origen="TRABAJO_GRADO", estado="PROPUESTA")


@pytest.mark.parametrize(
    "origen,estado",
    [
        ("SEMILLERO", "PROPUESTA"),
        ("SEMILLERO", "EN_CURSO"),
        ("SEMILLERO", "TERMINADO"),
        ("TRABAJO_GRADO", "EN_CURSO"),
        ("TRABAJO_GRADO", "TERMINADO"),
    ],
)
def test_combinaciones_validas_de_origen_y_estado(origen, estado):
    ProyectoFactory(origen=origen, estado=estado)


def test_check_constraint_tambien_bloquea_update():
    proyecto = ProyectoFactory(origen="TRABAJO_GRADO", estado="EN_CURSO")
    with falla_integridad():
        Proyecto.objects.filter(pk=proyecto.pk).update(estado="PROPUESTA")


# RN-25
def test_docente_no_puede_asignarse_dos_veces_al_mismo_proyecto():
    asignacion = AsignacionFactory()
    with falla_integridad():
        Asignacion.objects.create(proyecto=asignacion.proyecto, docente=asignacion.docente)


def test_autor_con_cedula_repetida_en_el_mismo_proyecto():
    autor = AutorFactory(cedula="123")
    with falla_integridad():
        AutorFactory(proyecto=autor.proyecto, cedula="123")


# Unicidad de correo y cédula (RN-05)
def test_correo_unico():
    JuradoFactory(email="ana@udenar.edu.co")
    with falla_integridad():
        JuradoFactory(email="ana@udenar.edu.co")


def test_correo_unico_sin_importar_mayusculas():
    JuradoFactory(email="ana@udenar.edu.co")
    with falla_integridad():
        JuradoFactory(email="  ANA@Udenar.edu.co ")


def test_cedula_unica():
    JuradoFactory(cedula="1085000000")
    with falla_integridad():
        JuradoFactory(cedula="1085000000")


def test_varios_administradores_sin_cedula():
    Usuario.objects.create_superuser(email="a1@udenar.edu.co", password="x", nombre_completo="A1")
    Usuario.objects.create_superuser(email="a2@udenar.edu.co", password="x", nombre_completo="A2")
    assert Usuario.objects.filter(cedula__isnull=True).count() == 2


def test_jurado_nuevo_por_defecto_debe_cambiar_password():
    usuario = Usuario.objects.create_user(
        email="j@udenar.edu.co", password="1085", nombre_completo="J", cedula="1085"
    )
    assert usuario.rol == Usuario.Rol.JURADO
    assert usuario.debe_cambiar_password is True


def test_evento_protegido_si_tiene_proyectos():
    from django.db.models import ProtectedError

    proyecto = ProyectoFactory()
    with pytest.raises(ProtectedError):
        proyecto.evento.delete()


# Catálogo de áreas (sección 5)
def test_catalogo_de_areas_exacto():
    areas = list(AreaConocimiento.objects.order_by("id").values_list("programa", "nombre"))
    assert areas == [
        ("IS", "Ingeniería de software"),
        ("IS", "Redes y telemática"),
        ("IS", "Seguridad informática"),
        ("IS", "RV/RA"),
        ("IS", "Ciencia de datos e IA"),
        ("IE", "Control y automatización"),
        ("IC", "Vías, transporte y movilidad"),
        ("IC", "Geotecnia"),
    ]


def test_programa_se_deriva_del_area():
    area = AreaConocimiento.objects.get(nombre="Geotecnia")
    proyecto = ProyectoFactory(area=area)
    assert proyecto.area.get_programa_display() == "Ingeniería Civil"
    assert not hasattr(Proyecto, "programa")
