"""Fase 3: eventos (RN-01 a RN-03), áreas y docentes (RN-04 a RN-06, RN-09 a RN-11)."""

import pytest
from axes.models import AccessAttempt
from django.urls import URLPattern, URLResolver, get_resolver

from core.models import Usuario
from evaluaciones.models import Asignacion, Evento
from evaluaciones.services import asignaciones_de_jurado

from .conftest import cliente_de
from .factories import (
    AsignacionFactory,
    EvaluacionFactory,
    EventoFactory,
    JuradoFactory,
    ProyectoFactory,
)

pytestmark = pytest.mark.django_db

EVENTOS = "/api/admin/eventos/"
DOCENTES = "/api/admin/docentes/"


# ---------------------------------------------------------------- Permisos


def _rutas_admin(patrones, prefijo=""):
    for patron in patrones:
        if isinstance(patron, URLResolver):
            yield from _rutas_admin(patron.url_patterns, prefijo + str(patron.pattern))
        elif isinstance(patron, URLPattern) and (prefijo + str(patron.pattern)).startswith("api/admin/"):
            yield "/" + (prefijo + str(patron.pattern)).replace("<int:pk>", "1")


@pytest.mark.parametrize("metodo", ["get", "post", "patch", "delete"])
def test_jurado_recibe_403_en_todas_las_rutas_de_admin(metodo):
    jurado = JuradoFactory(debe_cambiar_password=False)
    client = cliente_de(jurado)
    rutas = list(_rutas_admin(get_resolver().url_patterns))
    assert len(rutas) >= 10
    for ruta in rutas:
        r = getattr(client, metodo)(ruta, {}, format="json")
        assert r.status_code == 403, (metodo, ruta, r.status_code)
        assert r.json()["codigo"] == "PERMISO_DENEGADO"


def test_sin_sesion_recibe_401(api_client):
    assert api_client.get(EVENTOS).status_code == 401


# ---------------------------------------------------------------- Eventos


def test_crear_y_listar_eventos(admin_client):
    r = admin_client.post(EVENTOS, {"nombre": "I Encuentro", "fecha": "2026-10-09"}, format="json")
    assert r.status_code == 201
    assert r.json()["activo"] is False
    assert r.json()["num_proyectos"] == 0
    assert [e["nombre"] for e in admin_client.get(EVENTOS).json()] == ["I Encuentro"]


def test_crear_evento_valida_datos(admin_client):
    r = admin_client.post(EVENTOS, {"nombre": ""}, format="json")
    assert r.status_code == 400
    assert set(r.json()["campos"]) == {"nombre", "fecha"}


def test_rn02_activar_desactiva_los_demas(admin_client):
    a = EventoFactory(activo=True)
    b = EventoFactory()
    r = admin_client.post(f"{EVENTOS}{b.pk}/activar/")
    assert r.status_code == 200
    assert r.json()["activo"] is True
    a.refresh_from_db()
    assert a.activo is False
    assert list(Evento.objects.filter(activo=True)) == [b]


def test_rn02_crear_evento_activo_desactiva_el_anterior(admin_client):
    anterior = EventoFactory(activo=True)
    r = admin_client.post(EVENTOS, {"nombre": "Nuevo", "fecha": "2026-10-09", "activo": True}, format="json")
    assert r.json()["activo"] is True
    anterior.refresh_from_db()
    assert anterior.activo is False


def test_activar_dos_veces_es_idempotente(admin_client):
    evento = EventoFactory()
    admin_client.post(f"{EVENTOS}{evento.pk}/activar/")
    assert admin_client.post(f"{EVENTOS}{evento.pk}/activar/").status_code == 200
    assert Evento.objects.filter(activo=True).count() == 1


def test_activar_evento_inexistente(admin_client):
    assert admin_client.post(f"{EVENTOS}999/activar/").status_code == 404


def test_patch_evento_no_cambia_activo(admin_client):
    evento = EventoFactory()
    r = admin_client.patch(f"{EVENTOS}{evento.pk}/", {"nombre": "Renombrado", "activo": True}, format="json")
    assert r.status_code == 200
    assert r.json()["nombre"] == "Renombrado"
    assert r.json()["activo"] is False


def test_eliminar_evento_sin_proyectos(admin_client):
    evento = EventoFactory()
    assert admin_client.delete(f"{EVENTOS}{evento.pk}/").status_code == 204
    assert not Evento.objects.exists()


def test_rn01_no_se_elimina_evento_con_proyectos(admin_client):
    proyecto = ProyectoFactory()
    r = admin_client.delete(f"{EVENTOS}{proyecto.evento.pk}/")
    assert r.status_code == 409
    assert r.json()["codigo"] == "EVENTO_CON_PROYECTOS"


def test_rn03_jurado_solo_ve_asignaciones_del_evento_activo():
    jurado = JuradoFactory()
    activo, inactivo = EventoFactory(activo=True), EventoFactory()
    propia = AsignacionFactory(docente=jurado, proyecto=ProyectoFactory(evento=activo))
    AsignacionFactory(docente=jurado, proyecto=ProyectoFactory(evento=inactivo))
    AsignacionFactory(proyecto=ProyectoFactory(evento=activo))  # de otro jurado
    assert list(asignaciones_de_jurado(jurado)) == [propia]


# ---------------------------------------------------------------- Áreas


def test_areas_agrupadas_por_programa(admin_client):
    r = admin_client.get("/api/admin/areas/")
    assert r.status_code == 200
    grupos = r.json()
    assert [g["programa"] for g in grupos] == ["IS", "IE", "IC"]
    assert grupos[0]["programa_nombre"] == "Ingeniería de Sistemas"
    assert len(grupos[0]["areas"]) == 5
    assert [a["nombre"] for a in grupos[2]["areas"]] == ["Vías, transporte y movilidad", "Geotecnia"]


# ---------------------------------------------------------------- Docentes

DATOS_DOCENTE = {
    "nombre_completo": "Docente de Ejemplo",
    "cedula": "1000000001",
    "email": "Docente.Ejemplo@udenar.edu.co",
    "departamento": "Sistemas",
}


def test_rn04_rn05_rn06_crear_docente(admin_client, api_client):
    r = admin_client.post(DOCENTES, DATOS_DOCENTE, format="json")
    assert r.status_code == 201
    datos = r.json()
    assert datos["email"] == "docente.ejemplo@udenar.edu.co"
    assert datos["debe_cambiar_password"] is True
    assert datos["asignados"] == 0 and datos["max_asignaciones"] == 3
    docente = Usuario.objects.get(pk=datos["id"])
    assert docente.rol == "JURADO"
    assert docente.check_password("1000000001")  # RN-06
    login = api_client.post(
        "/api/auth/login/", {"email": "docente.ejemplo@udenar.edu.co", "password": "1000000001"}, format="json"
    )
    assert login.status_code == 200


@pytest.mark.parametrize("faltante", ["nombre_completo", "cedula", "email", "departamento"])
def test_rn04_todos_los_datos_son_obligatorios(admin_client, faltante):
    datos = {k: v for k, v in DATOS_DOCENTE.items() if k != faltante}
    r = admin_client.post(DOCENTES, datos, format="json")
    assert r.status_code == 400
    assert faltante in r.json()["campos"]


@pytest.mark.parametrize("departamento", ["Departamento de Sistemas", "sistemas", "Civil", "Mecánica"])
def test_departamento_solo_de_la_lista(admin_client, departamento):
    r = admin_client.post(DOCENTES, {**DATOS_DOCENTE, "departamento": departamento}, format="json")
    assert r.status_code == 400
    assert r.json()["campos"]["departamento"] == [
        "Elija un departamento de la lista: Sistemas, Ingeniería Civil o Electrónica."
    ]


@pytest.mark.parametrize("departamento", ["Sistemas", "Ingeniería Civil", "Electrónica"])
def test_departamentos_validos(admin_client, departamento):
    r = admin_client.post(DOCENTES, {**DATOS_DOCENTE, "departamento": departamento}, format="json")
    assert r.status_code == 201
    assert r.json()["departamento"] == departamento


def test_rn05_correo_y_cedula_unicos(admin_client):
    admin_client.post(DOCENTES, DATOS_DOCENTE, format="json")
    r = admin_client.post(DOCENTES, {**DATOS_DOCENTE, "email": "docente.ejemplo@UDENAR.edu.co"}, format="json")
    assert r.status_code == 400
    assert set(r.json()["campos"]) == {"email", "cedula"}


def test_cedula_con_puntos_es_rechazada(admin_client):
    r = admin_client.post(DOCENTES, {**DATOS_DOCENTE, "cedula": "1.085.246.810"}, format="json")
    assert r.status_code == 400
    assert "cedula" in r.json()["campos"]


def test_listado_con_carga_en_evento_activo_y_buscador(admin_client):
    activo, viejo = EventoFactory(activo=True), EventoFactory()
    ana = JuradoFactory(nombre_completo="Ana Gómez")
    JuradoFactory(nombre_completo="Luis Pérez")
    AsignacionFactory(docente=ana, proyecto=ProyectoFactory(evento=activo))
    AsignacionFactory(docente=ana, proyecto=ProyectoFactory(evento=activo))
    AsignacionFactory(docente=ana, proyecto=ProyectoFactory(evento=viejo))  # no cuenta
    datos = admin_client.get(DOCENTES).json()
    assert [(d["nombre_completo"], d["asignados"]) for d in datos] == [("Ana Gómez", 2), ("Luis Pérez", 0)]
    assert [d["nombre_completo"] for d in admin_client.get(DOCENTES, {"q": "pére"}).json()] == ["Luis Pérez"]


def test_listado_no_incluye_administradores(admin_client):
    JuradoFactory()
    assert all(d["email"].startswith("docente") for d in admin_client.get(DOCENTES).json())
    assert len(admin_client.get(DOCENTES).json()) == 1


def test_rn10_editar_cedula_no_cambia_la_contrasena(admin_client):
    docente = JuradoFactory(cedula="1111111", password="Mi-Clave-Propia-2026", debe_cambiar_password=False)
    r = admin_client.patch(f"{DOCENTES}{docente.pk}/", {"cedula": "2222222", "departamento": "Ingeniería Civil"}, format="json")
    assert r.status_code == 200
    docente.refresh_from_db()
    assert docente.cedula == "2222222"
    assert docente.departamento == "Ingeniería Civil"
    assert docente.check_password("Mi-Clave-Propia-2026")
    assert docente.debe_cambiar_password is False


def test_editar_docente_con_correo_de_otro(admin_client):
    JuradoFactory(email="otro@udenar.edu.co")
    docente = JuradoFactory()
    r = admin_client.patch(f"{DOCENTES}{docente.pk}/", {"email": "OTRO@udenar.edu.co"}, format="json")
    assert r.status_code == 400
    assert "email" in r.json()["campos"]


def test_editar_docente_sin_cambiar_correo_propio(admin_client):
    docente = JuradoFactory(email="yo@udenar.edu.co")
    r = admin_client.patch(f"{DOCENTES}{docente.pk}/", {"email": "yo@udenar.edu.co"}, format="json")
    assert r.status_code == 200


def test_rn11_no_se_elimina_docente_con_evaluaciones(admin_client):
    evaluacion = EvaluacionFactory()
    docente = evaluacion.asignacion.docente
    r = admin_client.delete(f"{DOCENTES}{docente.pk}/")
    assert r.status_code == 409
    assert r.json()["codigo"] == "DOCENTE_CON_EVALUACIONES"
    assert Usuario.objects.filter(pk=docente.pk).exists()


def test_eliminar_docente_sin_asignaciones(admin_client):
    docente = JuradoFactory()
    assert admin_client.delete(f"{DOCENTES}{docente.pk}/").status_code == 204
    assert not Usuario.objects.filter(pk=docente.pk).exists()


def test_docente_con_asignaciones_se_reemplaza_antes_de_eliminarlo(admin_client):
    """Eliminarlo dejaría proyectos con un solo jurado."""
    asignacion = AsignacionFactory()
    r = admin_client.delete(f"{DOCENTES}{asignacion.docente.pk}/")
    assert r.status_code == 409
    assert r.json()["codigo"] == "DOCENTE_CON_ASIGNACIONES"
    assert Asignacion.objects.filter(pk=asignacion.pk).exists()


def test_no_se_puede_gestionar_un_admin_como_docente(admin_client):
    from .factories import AdminFactory

    otro_admin = AdminFactory()
    assert admin_client.delete(f"{DOCENTES}{otro_admin.pk}/").status_code == 404


def test_rn09_restablecer_password(admin_client, api_client):
    docente = JuradoFactory(cedula="1085777777", password="Mi-Clave-Propia-2026", debe_cambiar_password=False)
    r = admin_client.post(f"{DOCENTES}{docente.pk}/restablecer-password/")
    assert r.status_code == 200
    docente.refresh_from_db()
    assert docente.check_password("1085777777")
    assert docente.debe_cambiar_password is True


def test_rn09_restablecer_levanta_el_bloqueo_de_axes(admin_client, api_client):
    docente = JuradoFactory(email="bloqueado@udenar.edu.co", cedula="1085888888", debe_cambiar_password=False)
    for _ in range(5):
        api_client.post("/api/auth/login/", {"email": "bloqueado@udenar.edu.co", "password": "mala"}, format="json")
    bloqueado = api_client.post(
        "/api/auth/login/", {"email": "bloqueado@udenar.edu.co", "password": "1085888888"}, format="json"
    )
    assert bloqueado.status_code == 429

    admin_client.post(f"{DOCENTES}{docente.pk}/restablecer-password/")

    assert not AccessAttempt.objects.filter(username="bloqueado@udenar.edu.co").exists()
    r = api_client.post(
        "/api/auth/login/", {"email": "bloqueado@udenar.edu.co", "password": "1085888888"}, format="json"
    )
    assert r.status_code == 200
    assert r.json()["usuario"]["debe_cambiar_password"] is True
