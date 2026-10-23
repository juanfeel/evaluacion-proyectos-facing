from io import StringIO

import pytest
from axes.models import AccessAttempt
from django.core.management import call_command

from core.models import Usuario
from evaluaciones.models import AreaConocimiento, Asignacion, Criterio, DescriptorCriterio, Evaluacion, Evento, Proyecto

from .factories import AdminFactory, AutorFactory, EvaluacionFactory, JuradoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def datos_de_prueba(api_client):
    admin = AdminFactory(email="admin@udenar.edu.co")
    evaluacion = EvaluacionFactory()
    AutorFactory(proyecto=evaluacion.asignacion.proyecto)
    JuradoFactory()  # sin asignaciones
    api_client.post("/api/auth/login/", {"email": "nadie@x.co", "password": "x"}, format="json")
    return admin


def test_sin_confirmar_solo_simula(datos_de_prueba):
    salida = StringIO()
    call_command("preparar_carga_real", stdout=salida)
    assert "Simulación: no se borró nada" in salida.getvalue()
    assert "Proyectos: 1" in salida.getvalue()
    assert Evaluacion.objects.count() == 1 and Proyecto.objects.exists()


def test_con_confirmar_deja_la_base_lista(datos_de_prueba):
    call_command("preparar_carga_real", "--confirmar", stdout=StringIO())
    assert not Evento.objects.exists()
    assert not Proyecto.objects.exists()
    assert not Asignacion.objects.exists()
    assert not Evaluacion.objects.exists()
    assert not Usuario.objects.filter(rol="JURADO").exists()
    assert not AccessAttempt.objects.exists()
    # Se conservan el admin, las áreas y la rúbrica.
    assert list(Usuario.objects.values_list("email", flat=True)) == ["admin@udenar.edu.co"]
    assert AreaConocimiento.objects.count() == 8
    assert Criterio.objects.count() == 14 and DescriptorCriterio.objects.count() == 22
