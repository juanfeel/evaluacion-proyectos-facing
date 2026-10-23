"""Fase 4: API del jurado y evaluación (RN-29 a RN-40)."""

import json
from decimal import Decimal

import pytest

from evaluaciones.models import Asistencia, Criterio, DetalleEvaluacion, Evaluacion

from .conftest import cliente_de
from .factories import AdminFactory, AsignacionFactory, AutorFactory, EventoFactory, JuradoFactory, ProyectoFactory

pytestmark = pytest.mark.django_db


def url(asignacion, recurso=""):
    return f"/api/jurado/asignaciones/{asignacion.pk}/{recurso}"


@pytest.fixture
def evento():
    return EventoFactory(activo=True)


@pytest.fixture
def proyecto(evento):
    p = ProyectoFactory(evento=evento, tipo="INV", estado="EN_CURSO", codigo="IS-07", titulo="Detección de fallas")
    AutorFactory(proyecto=p, nombre_completo="Laura Gómez", cedula="1085100001", orden=1)
    AutorFactory(proyecto=p, nombre_completo="Pedro Ruiz", cedula="1085100002", orden=2)
    return p


@pytest.fixture
def jurado_a():
    return JuradoFactory(nombre_completo="Jurado A", email="a@udenar.edu.co", debe_cambiar_password=False)


@pytest.fixture
def jurado_b():
    return JuradoFactory(nombre_completo="Jurado B", email="b@udenar.edu.co", debe_cambiar_password=False)


@pytest.fixture
def asignacion_a(proyecto, jurado_a):
    return AsignacionFactory(proyecto=proyecto, docente=jurado_a)


@pytest.fixture
def asignacion_b(proyecto, jurado_b):
    return AsignacionFactory(proyecto=proyecto, docente=jurado_b)


@pytest.fixture
def cliente_a(jurado_a):
    return cliente_de(jurado_a)


def payload(proyecto, nivel=3, asistio=True, **extra):
    criterios = Criterio.objects.filter(tipo=proyecto.tipo).order_by("orden")
    niveles = nivel if isinstance(nivel, dict) else {c.orden: nivel for c in criterios}
    return {
        "niveles": {str(c.pk): niveles[c.orden] for c in criterios if c.orden in niveles},
        "asistencia": {str(a.pk): asistio for a in proyecto.autores.all()},
        "fortalezas": "Buen póster",
        "aspectos_mejorar": "Ampliar la muestra",
        **extra,
    }


# ---------------------------------------------------------------- Listado


def test_listado_de_mis_asignaciones(cliente_a, asignacion_a, asignacion_b, evento):
    otra_propia = AsignacionFactory(docente=asignacion_a.docente, proyecto=ProyectoFactory(evento=evento, codigo="AA-1"))
    AsignacionFactory(docente=asignacion_a.docente, proyecto=ProyectoFactory(evento=EventoFactory()))  # RN-03
    r = cliente_a.get("/api/jurado/asignaciones/")
    assert r.status_code == 200
    datos = r.json()
    assert [a["id"] for a in datos] == [otra_propia.pk, asignacion_a.pk]
    item = datos[1]
    assert item["evaluada"] is False and item["enviada"] is None
    assert item["proyecto"]["codigo"] == "IS-07"
    assert item["proyecto"]["tipo"] == "INV" and item["proyecto"]["estado_nombre"] == "En curso"
    assert item["proyecto"]["programa"] == "Ingeniería de Sistemas"


def test_listado_marca_evaluada(cliente_a, asignacion_a, proyecto):
    cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto), format="json")
    item = cliente_a.get("/api/jurado/asignaciones/").json()[0]
    assert item["evaluada"] is True and item["enviada"] is not None


def test_admin_no_usa_rutas_de_jurado(asignacion_a):
    admin = cliente_de(AdminFactory())
    assert admin.get("/api/jurado/asignaciones/").status_code == 403
    assert admin.get(url(asignacion_a, "formulario/")).status_code == 403


# ---------------------------------------------------------------- RN-29


@pytest.mark.parametrize("recurso,metodo", [("formulario/", "get"), ("evaluacion/", "get"), ("evaluacion/", "post")])
def test_rn29_jurado_a_no_accede_a_la_asignacion_de_b(cliente_a, asignacion_a, asignacion_b, proyecto, recurso, metodo):
    r = getattr(cliente_a, metodo)(url(asignacion_b, recurso), payload(proyecto), format="json")
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"
    assert not Evaluacion.objects.filter(asignacion=asignacion_b).exists()


def test_rn03_asignacion_de_evento_inactivo_responde_404(cliente_a, jurado_a):
    vieja = AsignacionFactory(docente=jurado_a, proyecto=ProyectoFactory(evento=EventoFactory()))
    assert cliente_a.get(url(vieja, "formulario/")).status_code == 404


# ---------------------------------------------------------------- RN-30: formulario


def test_formulario_inv_en_curso(cliente_a, asignacion_a):
    r = cliente_a.get(url(asignacion_a, "formulario/"))
    assert r.status_code == 200
    f = r.json()
    assert f["evaluada"] is False
    assert f["proyecto"]["codigo"] == "IS-07"
    assert f["autores"] == [
        {"id": f["autores"][0]["id"], "nombre_completo": "Laura Gómez", "orden": 1},
        {"id": f["autores"][1]["id"], "nombre_completo": "Pedro Ruiz", "orden": 2},
    ]  # sin cédulas
    assert f["niveles"] == ["Insuficiente", "Básico", "Bueno", "Sobresaliente"]
    assert [c["nombre"] for c in f["criterios"]][2:4] == ["Diseño en ejecución", "Avances obtenidos hasta la fecha"]
    assert f["nota_estado"].startswith("En los criterios 3 y 4, valore el diseño en ejecución")
    assert f["asistencia_alguno"].startswith("Si al menos un ponente se presentó")
    assert f["asistencia_ninguno"].startswith("Si ningún ponente se presentó")


def test_formulario_dti_propuesta_trae_textos_de_propuesta(jurado_a, evento):
    p = ProyectoFactory(evento=evento, tipo="DTI", estado="PROPUESTA", origen="SEMILLERO")
    a = AsignacionFactory(proyecto=p, docente=jurado_a)
    f = cliente_de(jurado_a).get(url(a, "formulario/")).json()
    nombres = [c["nombre"] for c in f["criterios"]]
    assert nombres[3] == "Madurez esperada y viabilidad"
    assert nombres[4] == "Aplicabilidad prevista y trabajo futuro"
    assert nombres[2] == "Enfoque técnico"  # sin descriptor PROPUESTA → BASE
    assert f["criterios"][3]["descriptores"][0] == "Sin plan de desarrollo ni madurez esperada"
    assert f["criterios"][4]["puntajes"] == [0, 3, 7, 10]
    assert f["nota_estado"] is None


# ---------------------------------------------------------------- Envío


def test_envio_correcto(cliente_a, asignacion_a, proyecto):
    niveles = {1: 3, 2: 2, 3: 1, 4: 0, 5: 3, 6: 2, 7: 1}  # 15+10+7+0+10+10+5 = 57
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, niveles), format="json")
    assert r.status_code == 201, r.json()
    e = r.json()
    assert e["total"] == "57.00"
    assert e["sin_sustentacion"] is False
    assert [d["puntaje"] for d in e["detalles"]] == [15, 10, 7, 0, 10, 10, 5]
    assert e["detalles"][2]["nombre_criterio"] == "Diseño en ejecución"
    assert e["detalles"][0]["nivel_nombre"] == "Sobresaliente"
    assert e["fortalezas"] == "Buen póster"
    assert [a["asistio"] for a in e["asistencias"]] == [True, True]


def test_rn35_total_del_cliente_se_ignora(cliente_a, asignacion_a, proyecto):
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 0, total=100), format="json")
    assert r.status_code == 201
    assert r.json()["total"] == "0.00"
    assert Evaluacion.objects.get().total == Decimal("0.00")


def test_rn31_falta_un_criterio(cliente_a, asignacion_a, proyecto):
    niveles = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3}  # falta el 7
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, niveles), format="json")
    assert r.status_code == 400
    assert r.json()["campos"]["niveles"] == ["Falta elegir el nivel de los criterios: 7."]
    assert not Evaluacion.objects.exists()


@pytest.mark.parametrize("valor", [4, -1, "3", 2.5, True, None])
def test_rn31_nivel_fuera_de_rango(cliente_a, asignacion_a, proyecto, valor):
    datos = payload(proyecto)
    datos["niveles"][next(iter(datos["niveles"]))] = valor
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json")
    assert r.status_code == 400
    assert "niveles" in r.json()["campos"]


def test_rn31_criterio_de_otra_rubrica(cliente_a, asignacion_a, proyecto):
    datos = payload(proyecto)
    datos["niveles"][str(Criterio.objects.get(tipo="DTI", orden=1).pk)] = 3
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json")
    assert r.status_code == 400


def test_rn32_falta_una_marca_de_asistencia(cliente_a, asignacion_a, proyecto):
    datos = payload(proyecto)
    datos["asistencia"].pop(next(iter(datos["asistencia"])))
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json")
    assert r.status_code == 400
    assert r.json()["campos"]["asistencia"] == ["Falta marcar la asistencia de: Laura Gómez."]


def test_rn32_asistencia_debe_ser_booleana(cliente_a, asignacion_a, proyecto):
    datos = payload(proyecto, asistio="sí")
    assert cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json").status_code == 400


def test_falta_todo(cliente_a, asignacion_a):
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), {}, format="json")
    assert r.status_code == 400
    assert {"niveles", "asistencia"} <= set(r.json()["campos"])


def test_rn33_nadie_asistio_fuerza_criterio_7_en_cero(cliente_a, asignacion_a, proyecto):
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 3, asistio=False), format="json")
    assert r.status_code == 201
    e = r.json()
    assert e["sin_sustentacion"] is True
    assert e["detalles"][6]["nivel"] == 0 and e["detalles"][6]["puntaje"] == 0
    assert e["total"] == "85.00"
    assert [a["asistio"] for a in e["asistencias"]] == [False, False]


def test_rn33_basta_un_asistente(cliente_a, asignacion_a, proyecto):
    datos = payload(proyecto, 3)
    primero = next(iter(datos["asistencia"]))
    datos["asistencia"] = {k: k == primero for k in datos["asistencia"]}
    e = cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json").json()
    assert e["sin_sustentacion"] is False
    assert e["total"] == "100.00"


def test_rn34_observaciones_opcionales(cliente_a, asignacion_a, proyecto):
    datos = payload(proyecto)
    del datos["fortalezas"], datos["aspectos_mejorar"]
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json")
    assert r.status_code == 201
    assert r.json()["fortalezas"] == "" and r.json()["aspectos_mejorar"] == ""


def test_rn38_segundo_envio_responde_409(cliente_a, asignacion_a, proyecto):
    primero = cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 3), format="json")
    assert primero.status_code == 201
    segundo = cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 0), format="json")
    assert segundo.status_code == 409
    assert segundo.json()["codigo"] == "EVALUACION_YA_ENVIADA"
    assert Evaluacion.objects.count() == 1
    assert Evaluacion.objects.get().total == Decimal("100.00")


@pytest.mark.parametrize("metodo", ["put", "patch", "delete"])
def test_rn36_no_hay_edicion_ni_borrado(cliente_a, asignacion_a, proyecto, metodo):
    cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 3), format="json")
    r = getattr(cliente_a, metodo)(url(asignacion_a, "evaluacion/"), payload(proyecto, 0), format="json")
    assert r.status_code == 405
    assert r.json()["codigo"] == "METODO_NO_PERMITIDO"
    assert Evaluacion.objects.get().total == Decimal("100.00")


def test_rn39_la_evaluacion_guarda_copias(cliente_a, asignacion_a, proyecto):
    cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 3), format="json")
    # Cambios futuros en la rúbrica y en los autores no alteran lo guardado.
    criterio = Criterio.objects.get(tipo="INV", orden=1)
    criterio.puntajes = [0, 1, 2, 3]
    criterio.save()
    autor = proyecto.autores.get(orden=1)
    autor.nombre_completo = "Otro nombre"
    autor.save()
    e = cliente_a.get(url(asignacion_a, "evaluacion/")).json()
    assert e["detalles"][0]["puntaje"] == 15
    assert e["total"] == "100.00"
    assert e["asistencias"][0]["nombre_autor"] == "Laura Gómez"
    assert DetalleEvaluacion.objects.count() == 7 and Asistencia.objects.count() == 2


def test_consultar_evaluacion_propia(cliente_a, asignacion_a, proyecto):
    r = cliente_a.get(url(asignacion_a, "evaluacion/"))
    assert r.status_code == 404 and r.json()["codigo"] == "SIN_EVALUACION"
    cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 2), format="json")
    r = cliente_a.get(url(asignacion_a, "evaluacion/"))
    assert r.status_code == 200
    assert r.json()["total"] == "67.00"  # nivel Bueno: 10+10+13+7+7+10+10


# ---------------------------------------------------------------- RN-40


def test_rn40_el_jurado_no_ve_la_nota_del_otro(asignacion_a, asignacion_b, proyecto, jurado_a, jurado_b):
    cliente_b = cliente_de(jurado_b)
    cliente_b.post(url(asignacion_b, "evaluacion/"), payload(proyecto, 1, fortalezas="SECRETO-DE-B"), format="json")
    total_b = str(Evaluacion.objects.get(asignacion=asignacion_b).total)

    cliente_a = cliente_de(jurado_a)
    respuestas = [
        cliente_a.get("/api/jurado/asignaciones/"),
        cliente_a.get(url(asignacion_a, "formulario/")),
        cliente_a.post(url(asignacion_a, "evaluacion/"), payload(proyecto, 3), format="json"),
        cliente_a.get(url(asignacion_a, "evaluacion/")),
        cliente_a.get("/api/auth/me/"),
    ]
    for r in respuestas:
        assert r.status_code in (200, 201)
        texto = json.dumps(r.json(), ensure_ascii=False)
        assert "SECRETO-DE-B" not in texto
        assert "Jurado B" not in texto and "b@udenar.edu.co" not in texto
        assert total_b not in texto
        assert "1085100001" not in texto  # cédulas de autores: solo el admin


def test_rubrica_incompleta_no_guarda_evaluaciones_vacias(cliente_a, asignacion_a, proyecto):
    datos = payload(proyecto)
    Criterio.objects.filter(tipo="INV", orden=7).delete()
    r = cliente_a.post(url(asignacion_a, "evaluacion/"), datos, format="json")
    assert r.status_code == 500
    assert r.json()["codigo"] == "RUBRICA_INCOMPLETA"
    assert not Evaluacion.objects.exists()
