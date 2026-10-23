"""Fase 5: resultados (RN-41 a RN-47), detalle de evaluaciones y resumen."""

from decimal import Decimal

import pytest

from evaluaciones.models import Criterio
from evaluaciones.services import promedio

from .conftest import cliente_de
from .factories import (
    AsignacionFactory,
    AutorFactory,
    EvaluacionFactory,
    EventoFactory,
    JuradoFactory,
    ProyectoFactory,
)

pytestmark = pytest.mark.django_db

RESULTADOS = "/api/admin/resultados/"


@pytest.fixture
def evento():
    return EventoFactory(activo=True)


def proyecto_con_notas(evento, codigo, *totales, origen="SEMILLERO", tipo="INV", sin_sust=(), jurados=2):
    """Proyecto con `jurados` asignados y una evaluación por cada total dado."""
    p = ProyectoFactory(evento=evento, codigo=codigo, origen=origen, tipo=tipo, estado="EN_CURSO")
    asignaciones = [AsignacionFactory(proyecto=p) for _ in range(jurados)]
    for i, total in enumerate(totales):
        EvaluacionFactory(asignacion=asignaciones[i], total=Decimal(str(total)), sin_sustentacion=i in sin_sust)
    return p


def tabla(datos, origen="SEMILLERO", tipo="INV"):
    return next(t for t in datos["tablas"] if t["origen"] == origen and t["tipo"] == tipo)["proyectos"]


def filas(client, **kw):
    r = client.get(RESULTADOS)
    assert r.status_code == 200, r.json()
    return tabla(r.json(), **kw)


# ---------------------------------------------------------------- RN-41


def test_rn41_solo_el_admin_ve_resultados(evento):
    jurado = JuradoFactory(debe_cambiar_password=False)
    for ruta in (RESULTADOS, "/api/admin/resumen/", f"/api/admin/proyectos/{ProyectoFactory().pk}/evaluaciones/"):
        assert cliente_de(jurado).get(ruta).status_code == 403


# ---------------------------------------------------------------- RN-42


@pytest.mark.parametrize("notas,esperado", [
    ((80, 81), "80.50"),
    ((77, 80), "78.50"),
    ((100, 100), "100.00"),
    ((0, 0), "0.00"),
    (("80.01", "80.00"), "80.01"),     # 80.005 → 80.01 (half-up, no al par)
    (("79.99", "80.00"), "80.00"),     # 79.995 → 80.00
])
def test_rn42_promedio_dos_decimales_half_up(admin_client, evento, notas, esperado):
    proyecto_con_notas(evento, "P", *notas)
    assert filas(admin_client)[0]["promedio"] == esperado


def test_rn42_funcion_promedio_usa_half_up():
    assert promedio([Decimal("0.005"), Decimal("0.000")]) == Decimal("0.00")
    assert promedio([Decimal("0.01"), Decimal("0.00")]) == Decimal("0.01")  # 0.005 → 0.01 (bancario daría 0.00)
    assert promedio([Decimal("0.03"), Decimal("0.00")]) == Decimal("0.02")  # 0.015 → 0.02


def test_rn42_notas_de_cada_jurado(admin_client, evento):
    proyecto_con_notas(evento, "P", 81, 80)
    fila = filas(admin_client)[0]
    assert (fila["nota_jurado_1"], fila["nota_jurado_2"], fila["promedio"]) == ("81.00", "80.00", "80.50")


# ---------------------------------------------------------------- RN-44: 4 tablas


def test_rn44_cuatro_tablas_con_los_proyectos_correctos(admin_client, evento):
    proyecto_con_notas(evento, "S-INV", 90, 90, origen="SEMILLERO", tipo="INV")
    proyecto_con_notas(evento, "S-DTI", 90, 90, origen="SEMILLERO", tipo="DTI")
    proyecto_con_notas(evento, "T-INV", 90, 90, origen="TRABAJO_GRADO", tipo="INV")
    proyecto_con_notas(evento, "T-DTI-1", 90, 90, origen="TRABAJO_GRADO", tipo="DTI")
    proyecto_con_notas(evento, "T-DTI-2", 80, 80, origen="TRABAJO_GRADO", tipo="DTI")
    proyecto_con_notas(EventoFactory(), "OTRO-EVENTO", 90, 90)
    datos = admin_client.get(RESULTADOS).json()
    assert [(t["origen"], t["tipo"], t["titulo"]) for t in datos["tablas"]] == [
        ("SEMILLERO", "INV", "Semillero de investigación · INV"),
        ("SEMILLERO", "DTI", "Semillero de investigación · DTI"),
        ("TRABAJO_GRADO", "INV", "Trabajo de grado · INV"),
        ("TRABAJO_GRADO", "DTI", "Trabajo de grado · DTI"),
    ]
    assert [[p["codigo"] for p in t["proyectos"]] for t in datos["tablas"]] == [
        ["S-INV"], ["S-DTI"], ["T-INV"], ["T-DTI-1", "T-DTI-2"]
    ]
    assert datos["evento"]["id"] == evento.pk


def test_resultados_de_otro_evento_por_parametro(admin_client, evento):
    otro = EventoFactory()
    proyecto_con_notas(otro, "VIEJO", 70, 70)
    r = admin_client.get(RESULTADOS, {"evento": otro.pk}).json()
    assert tabla(r)[0]["codigo"] == "VIEJO"


def test_sin_evento_activo_pide_el_evento(admin_client):
    r = admin_client.get(RESULTADOS)
    assert r.status_code == 400
    assert r.json()["codigo"] == "SIN_EVENTO_ACTIVO"


def test_tablas_vacias(admin_client, evento):
    assert all(t["proyectos"] == [] for t in admin_client.get(RESULTADOS).json()["tablas"])


# ---------------------------------------------------------------- RN-45: orden y empates


def test_rn45_empates_comparten_puesto_y_el_siguiente_salta(admin_client, evento):
    proyecto_con_notas(evento, "C", 85, 85)
    proyecto_con_notas(evento, "A", 90, 90)
    proyecto_con_notas(evento, "B", 95, 85)  # también 90.00
    resultado = [(f["codigo"], f["promedio"], f["puesto"]) for f in filas(admin_client)]
    assert resultado == [("A", "90.00", 1), ("B", "90.00", 1), ("C", "85.00", 3)]


def test_rn45_orden_de_mayor_a_menor_y_empates_multiples(admin_client, evento):
    for codigo, nota in [("P1", 70), ("P2", 99), ("P3", 80), ("P4", 80), ("P5", 80), ("P6", 60)]:
        proyecto_con_notas(evento, codigo, nota, nota)
    assert [f["puesto"] for f in filas(admin_client)] == [1, 2, 2, 2, 5, 6]


# ---------------------------------------------------------------- RN-43: pendientes


def test_rn43_pendientes_al_final_sin_puesto(admin_client, evento):
    proyecto_con_notas(evento, "Z-PARCIAL", 100)            # 1 de 2
    proyecto_con_notas(evento, "A-SIN-JURADOS", jurados=0)
    proyecto_con_notas(evento, "M-PENDIENTE")               # 2 asignados, 0 evaluaciones
    proyecto_con_notas(evento, "B-BAJO", 10, 10)
    datos = filas(admin_client)
    assert [(f["codigo"], f["puesto"], f["pendiente"]) for f in datos] == [
        ("B-BAJO", 1, False),
        ("A-SIN-JURADOS", None, True),
        ("M-PENDIENTE", None, True),
        ("Z-PARCIAL", None, True),
    ]
    parcial = datos[3]
    assert (parcial["nota_jurado_1"], parcial["nota_jurado_2"], parcial["promedio"]) == ("100.00", None, None)
    assert parcial["reconocimiento"] is False and parcial["mencion_meritoria"] is False


# ---------------------------------------------------------------- RN-46: indicadores en los bordes


@pytest.mark.parametrize("notas,reconocimiento,mencion", [
    (("79.99", "79.99"), False, False),
    (("80.00", "80.00"), True, False),
    (("84.99", "84.99"), True, False),
    (("85.00", "85.00"), True, True),
    (("79.98", "80.00"), False, False),   # 79.99
    (("80", "81"), True, False),          # 80.50
    (("84.99", "85.00"), True, True),     # 84.995 → 85.00 por half-up
])
def test_rn46_reconocimiento_y_mencion_en_los_bordes(admin_client, evento, notas, reconocimiento, mencion):
    proyecto_con_notas(evento, "P", *notas)
    fila = filas(admin_client)[0]
    assert (fila["reconocimiento"], fila["mencion_meritoria"], fila["sin_sustentacion"]) == (
        reconocimiento, mencion, False
    )


@pytest.mark.parametrize("sin_sust", [(0,), (1,), (0, 1)])
def test_rn46_sin_sustentacion_basta_una_evaluacion(admin_client, evento, sin_sust):
    proyecto_con_notas(evento, "P", 95, 95, sin_sust=sin_sust)
    fila = filas(admin_client)[0]
    assert fila["sin_sustentacion"] is True
    assert fila["reconocimiento"] is False
    assert fila["mencion_meritoria"] is False
    assert fila["puesto"] == 1  # sigue en el ranking


def test_rn46_sin_sustentacion_visible_aunque_este_pendiente(admin_client, evento):
    proyecto_con_notas(evento, "P", 50, sin_sust=(0,))
    fila = filas(admin_client)[0]
    assert fila["pendiente"] is True and fila["sin_sustentacion"] is True


def test_umbrales_en_la_respuesta(admin_client, evento):
    assert admin_client.get(RESULTADOS).json()["umbrales"] == {"reconocimiento": "80.00", "mencion_meritoria": "85.00"}


# ---------------------------------------------------------------- RN-47: detalle


def test_rn47_detalle_con_ambas_evaluaciones_completas(admin_client, evento):
    p = ProyectoFactory(evento=evento, tipo="DTI", estado="TERMINADO", origen="TRABAJO_GRADO")
    autores = [AutorFactory(proyecto=p, nombre_completo=n, orden=i) for i, n in enumerate(["Ana", "Beto"], 1)]
    from evaluaciones.services import registrar_evaluacion

    j1, j2 = JuradoFactory(nombre_completo="Jurado Uno"), JuradoFactory(nombre_completo="Jurado Dos")
    a1, a2 = AsignacionFactory(proyecto=p, docente=j1), AsignacionFactory(proyecto=p, docente=j2)
    criterios = Criterio.objects.filter(tipo="DTI")
    registrar_evaluacion(a1.pk, {c.pk: 3 for c in criterios}, {autores[0].pk: True, autores[1].pk: False},
                         "Fortaleza 1", "Mejora 1")
    registrar_evaluacion(a2.pk, {c.pk: 1 for c in criterios}, {a.pk: False for a in autores})

    r = admin_client.get(f"/api/admin/proyectos/{p.pk}/evaluaciones/")
    assert r.status_code == 200
    datos = r.json()
    assert datos["proyecto"]["codigo"] == p.codigo
    e1, e2 = datos["evaluaciones"]
    assert e1["jurado"]["nombre_completo"] == "Jurado Uno" and "email" in e1["jurado"]
    assert e1["total"] == "100.00" and e1["sin_sustentacion"] is False
    assert (e1["fortalezas"], e1["aspectos_mejorar"]) == ("Fortaleza 1", "Mejora 1")
    assert [(a["nombre_autor"], a["asistio"]) for a in e1["asistencias"]] == [("Ana", True), ("Beto", False)]
    assert len(e1["detalles"]) == 7 and e1["detalles"][0]["nivel_nombre"] == "Sobresaliente"
    assert e2["jurado"]["nombre_completo"] == "Jurado Dos"
    assert e2["sin_sustentacion"] is True and e2["detalles"][6]["puntaje"] == 0
    assert e2["total"] == "28.00"  # 5+5+7+3+3+5+0

    fila = tabla(admin_client.get(RESULTADOS).json(), "TRABAJO_GRADO", "DTI")[0]
    assert (fila["promedio"], fila["sin_sustentacion"], fila["reconocimiento"]) == ("64.00", True, False)


def test_rn47_proyecto_sin_evaluaciones(admin_client, evento):
    p = ProyectoFactory(evento=evento)
    assert admin_client.get(f"/api/admin/proyectos/{p.pk}/evaluaciones/").json()["evaluaciones"] == []


# ---------------------------------------------------------------- Resumen


def test_resumen_del_tablero(admin_client, evento):
    proyecto_con_notas(evento, "SJ", jurados=1)
    proyecto_con_notas(evento, "PE")
    proyecto_con_notas(evento, "PA", 80)
    proyecto_con_notas(evento, "EV1", 80, 90)
    proyecto_con_notas(evento, "EV2", 70, 60)
    proyecto_con_notas(EventoFactory(), "OTRO", 80, 80)
    r = admin_client.get("/api/admin/resumen/")
    assert r.status_code == 200
    assert r.json() == {
        "evento": {"id": evento.pk, "nombre": evento.nombre, "activo": True},
        "total_proyectos": 5,
        "sin_jurados": 1,
        "pendientes": 1,
        "parciales": 1,
        "evaluados": 2,
        "evaluaciones_enviadas": 5,
        "evaluaciones_total": 10,
    }


def test_resultados_sin_consultas_n_mas_1(admin_client, evento, django_assert_max_num_queries):
    for i in range(12):
        proyecto_con_notas(evento, f"P{i:02d}", 80, 90, origen=["SEMILLERO", "TRABAJO_GRADO"][i % 2])
    with django_assert_max_num_queries(8):
        assert admin_client.get(RESULTADOS).status_code == 200
