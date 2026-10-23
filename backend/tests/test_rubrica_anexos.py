"""Rúbrica vs. anexos 6 (Investigación) y 7 (DTI) actualizados.

Los valores esperados están ESCRITOS AQUÍ (copiados de la sección 6 de CLAUDE.md, ya corregida), no se
leen del YAML: así la prueba falla si el YAML, la migración o la API se apartan de los anexos.
Se verifica a través de la API real del jurado: GET /api/jurado/asignaciones/{id}/formulario/.
"""

import pytest

from evaluaciones.models import AreaConocimiento, Evento

from .conftest import cliente_de
from .factories import AsignacionFactory, AutorFactory, EventoFactory, JuradoFactory, ProyectoFactory

pytestmark = pytest.mark.django_db

PUNTAJES = {
    1: [0, 5, 10, 15],
    2: [0, 5, 10, 15],
    3: [0, 7, 13, 20],
    4: [0, 3, 7, 10],
    5: [0, 3, 7, 10],
    6: [0, 5, 10, 15],
    7: [0, 5, 10, 15],
}

POSTER = (
    "Calidad del póster",
    [
        "Ilegible a un metro, o incumple la plantilla institucional",
        "Legible, pero sobrecargado o con bloques incompletos",
        "Legible, ordenado y conforme a la plantilla",
        "Legible, ordenado, con figuras que aportan al contenido",
    ],
)
SUSTENTACION = (
    "Sustentación",
    [
        "No sustenta, o no domina el proyecto que presenta",
        "Expone con dificultad; responde parcialmente las preguntas",
        "Expone con claridad y responde las preguntas",
        "Expone con claridad, domina el tema y argumenta sus respuestas",
    ],
)

# ---------------------------------------------------------------- Anexo 6 · Investigación
INV_BASE = {
    1: (
        "Planteamiento del problema, objetivos y pertinencia",
        [
            "Problema difuso; objetivos ausentes o incoherentes con él",
            "Problema enunciado; objetivos vagos o sin relación clara",
            "Problema delimitado; objetivos precisos y coherentes",
            "Problema delimitado y pertinente; objetivos precisos y verificables",
        ],
    ),
    2: (
        "Antecedentes",
        [
            "Sin antecedentes, o ajenos al problema planteado",
            "Menciona fuentes aisladas, sin relación entre sí",
            "Revisión pertinente y actualizada, dentro de los 5 años",
            "Revisión pertinente que sitúa el vacío que el proyecto aborda",
        ],
    ),
    3: (
        "Rigor metodológico",
        [
            "Metodología ausente o que no corresponde al problema",
            "Metodología enunciada, sin instrumentos ni técnicas de análisis",
            "Metodología completa y coherente con el problema",
            "Metodología completa, coherente y justificada frente a alternativas",
        ],
    ),
    4: (
        "Resultados y avances",
        [
            "Sin resultados ni avances declarados",
            "Resultados enunciados, sin datos ni evidencia",
            "Resultados presentados con evidencia suficiente",
            "Resultados presentados, con evidencia y análisis",
        ],
    ),
    5: (
        "Conclusiones y trabajo futuro",
        [
            "Ausentes o sin relación con los resultados",
            "Enunciadas, sin sustento en los resultados",
            "Derivadas de los resultados, sin proyección",
            "Derivadas de los resultados, con líneas de continuidad claras",
        ],
    ),
    6: POSTER,
    7: SUSTENTACION,
}
INV_PLAN = [
    "Sin plan de trabajo ni resultados esperados",
    "Plan enunciado, sin fases ni recursos",
    "Plan con fases y recursos definidos",
    "Plan con fases, recursos y riesgos previstos",
]
INV_PROPUESTA = {
    **INV_BASE,
    4: ("Resultados esperados y viabilidad", INV_PLAN),
    5: (
        "Aportes previstos y trabajo futuro",
        [
            "Sin aportes previstos ni siguientes pasos",
            "Aportes enunciados de forma general",
            "Aportes previstos coherentes con los objetivos",
            "Aportes previstos coherentes, con siguientes pasos definidos",
        ],
    ),
}
INV_EN_CURSO = {
    **INV_BASE,
    3: ("Diseño en ejecución", INV_BASE[3][1]),  # descriptores de BASE
    4: ("Avances obtenidos hasta la fecha", INV_PLAN),  # descriptores de PROPUESTA
}

# ---------------------------------------------------------------- Anexo 7 · DTI
DTI_BASE = {
    1: (
        "Reto tecnológico, objetivos y pertinencia",
        [
            "Reto difuso; objetivos ausentes o incoherentes con él",
            "Reto enunciado; objetivos vagos o sin relación clara",
            "Reto delimitado; objetivos precisos y coherentes",
            "Reto delimitado y pertinente; objetivos precisos y verificables",
        ],
    ),
    2: (
        "Soluciones existentes y grado de novedad",
        [
            "Sin revisión de soluciones existentes",
            "Menciona soluciones aisladas, sin comparación",
            "Revisión pertinente y actualizada, dentro de los 5 años",
            "Revisión pertinente que sustenta el grado de novedad de la propuesta",
        ],
    ),
    3: (
        "Enfoque técnico",
        [
            "Enfoque ausente o que no corresponde al reto planteado",
            "Enfoque enunciado, sin componentes ni tecnologías definidas",
            "Arquitectura completa y coherente con el reto",
            "Arquitectura completa, coherente y justificada frente a alternativas",
        ],
    ),
    4: (
        "Nivel de madurez",
        [
            "Sin evidencia de avance del desarrollo",
            "Avance declarado, sin evidencia que lo respalde",
            "Nivel de madurez declarado y evidenciado",
            "Nivel de madurez evidenciado y validado",
        ],
    ),
    5: (
        "Aplicabilidad y transferencia",
        [
            "Sin aplicación identificada",
            "Aplicación enunciada de forma general",
            "Aplicación concreta identificada, con usuario o contexto",
            "Aplicación concreta con ruta de transferencia definida",
        ],
    ),
    6: POSTER,
    7: SUSTENTACION,
}
DTI_PLAN = [
    "Sin plan de desarrollo ni madurez esperada",
    "Plan enunciado, sin fases ni recursos",
    "Plan con fases y recursos definidos",
    "Plan con fases, recursos y riesgos previstos",
]
DTI_PROPUESTA = {
    **DTI_BASE,
    4: ("Madurez esperada y viabilidad", DTI_PLAN),
    5: (
        "Aplicabilidad prevista y trabajo futuro",
        [
            "Sin aplicación prevista",
            "Aplicación enunciada de forma general",
            "Aplicación prevista con usuario o contexto identificado",
            "Aplicación prevista con ruta de continuidad definida",
        ],
    ),
}
DTI_EN_CURSO = {
    **DTI_BASE,
    3: ("Enfoque en desarrollo, no el desarrollo concluido", DTI_BASE[3][1]),
    4: ("Madurez alcanzada a la fecha, no el desarrollo concluido", DTI_PLAN),
}

VARIANTES = {
    ("INV", "TERMINADO"): INV_BASE,
    ("INV", "PROPUESTA"): INV_PROPUESTA,
    ("INV", "EN_CURSO"): INV_EN_CURSO,
    ("DTI", "TERMINADO"): DTI_BASE,
    ("DTI", "PROPUESTA"): DTI_PROPUESTA,
    ("DTI", "EN_CURSO"): DTI_EN_CURSO,
}

NOTAS_ESTADO = {
    "INV": "En los criterios 3 y 4, valore el diseño en ejecución y los avances obtenidos a la fecha, no el trabajo terminado.",
    "DTI": "En los criterios 3 y 4, valore el enfoque en desarrollo y la madurez alcanzada a la fecha, no el desarrollo concluido.",
}
ASISTENCIA_ALGUNO = (
    "Si al menos un ponente se presentó, evalúe el proyecto completo. Los ponentes ausentes no reciben certificado "
    "de ponente, y ello no afecta la calificación del proyecto ni los certificados de los demás."
)
ASISTENCIA_NINGUNO = (
    "Si ningún ponente se presentó, califique los criterios 1 a 6; el criterio 7 queda en 0 y la evaluación se "
    "registra como «sin sustentación». El proyecto no aspira a los reconocimientos."
)
TEXTO_UMBRALES = "Umbral de reconocimiento: 80 puntos. Mención meritoria: 85 puntos."
NIVELES = ["Insuficiente", "Básico", "Bueno", "Sobresaliente"]


def formulario(tipo, estado):
    """Formulario real de la API para un proyecto de la variante dada."""
    evento = Evento.objects.filter(activo=True).first() or EventoFactory(activo=True)
    proyecto = ProyectoFactory(
        evento=evento, tipo=tipo, estado=estado, origen="SEMILLERO",
        area=AreaConocimiento.objects.get(nombre="Ingeniería de software"),
    )
    AutorFactory(proyecto=proyecto)
    jurado = JuradoFactory(debe_cambiar_password=False)
    asignacion = AsignacionFactory(proyecto=proyecto, docente=jurado)
    r = cliente_de(jurado).get(f"/api/jurado/asignaciones/{asignacion.pk}/formulario/")
    assert r.status_code == 200, r.json()
    return r.json()


@pytest.mark.parametrize("tipo,estado", list(VARIANTES))
def test_criterios_coinciden_con_los_anexos(tipo, estado):
    f = formulario(tipo, estado)
    esperado = VARIANTES[(tipo, estado)]
    assert [c["orden"] for c in f["criterios"]] == [1, 2, 3, 4, 5, 6, 7]
    for c in f["criterios"]:
        nombre, descriptores = esperado[c["orden"]]
        assert c["nombre"] == nombre, (tipo, estado, c["orden"])
        assert c["puntajes"] == PUNTAJES[c["orden"]], (tipo, estado, c["orden"])
        assert c["descriptores"] == descriptores, (tipo, estado, c["orden"])
    assert f["niveles"] == NIVELES


@pytest.mark.parametrize("tipo,estado", list(VARIANTES))
def test_sumas_maximo_100_minimo_0(tipo, estado):
    criterios = formulario(tipo, estado)["criterios"]
    assert sum(c["puntajes"][3] for c in criterios) == 100
    assert sum(c["puntajes"][0] for c in criterios) == 0


@pytest.mark.parametrize("tipo,estado", list(VARIANTES))
def test_nota_de_estado_solo_en_curso(tipo, estado):
    nota = formulario(tipo, estado)["nota_estado"]
    assert nota == (NOTAS_ESTADO[tipo] if estado == "EN_CURSO" else None)


@pytest.mark.parametrize("tipo,estado", list(VARIANTES))
def test_textos_de_asistencia_y_umbrales_exactos(tipo, estado):
    f = formulario(tipo, estado)
    assert f["asistencia_alguno"] == ASISTENCIA_ALGUNO
    assert f["asistencia_ninguno"] == ASISTENCIA_NINGUNO
    assert f["texto_umbrales"] == TEXTO_UMBRALES


@pytest.mark.parametrize("tipo", ["INV", "DTI"])
def test_que_cambia_en_cada_estado(tipo):
    """C1, C2, C6 y C7 nunca cambian; PROPUESTA cambia C4 y C5; EN_CURSO cambia C3 y C4 (rótulos)."""
    base, propuesta, en_curso = (VARIANTES[(tipo, e)] for e in ("TERMINADO", "PROPUESTA", "EN_CURSO"))
    rotulos = {e: [c["nombre"] for c in formulario(tipo, e)["criterios"]] for e in ("TERMINADO", "PROPUESTA", "EN_CURSO")}
    assert [i + 1 for i, (a, b) in enumerate(zip(rotulos["TERMINADO"], rotulos["PROPUESTA"])) if a != b] == [4, 5]
    assert [i + 1 for i, (a, b) in enumerate(zip(rotulos["TERMINADO"], rotulos["EN_CURSO"])) if a != b] == [3, 4]
    # Descriptores de EN_CURSO: C3 los de BASE, C4 los de PROPUESTA.
    assert en_curso[3][1] == base[3][1]
    assert en_curso[4][1] == propuesta[4][1]


@pytest.mark.parametrize("estado", ["EN_CURSO", "TERMINADO"])
def test_trabajo_de_grado_nunca_recibe_la_variante_propuesta(admin_client, estado):
    """RN-17: no se puede registrar ni editar un trabajo de grado en Propuesta."""
    evento = EventoFactory(activo=True)
    area = AreaConocimiento.objects.get(nombre="Geotecnia")
    datos = {
        "evento": evento.pk, "codigo": "TG-1", "titulo": "T", "area": area.pk, "origen": "TRABAJO_GRADO",
        "tipo": "INV", "estado": "PROPUESTA", "autores": [{"nombre_completo": "A", "cedula": "12345"}],
    }
    assert admin_client.post("/api/admin/proyectos/", datos, format="json").status_code == 400
    creado = admin_client.post("/api/admin/proyectos/", {**datos, "estado": estado}, format="json").json()
    r = admin_client.patch(f"/api/admin/proyectos/{creado['id']}/", {"estado": "PROPUESTA"}, format="json")
    assert r.status_code == 400
    jurados = [JuradoFactory(debe_cambiar_password=False) for _ in range(2)]
    admin_client.post(f"/api/admin/proyectos/{creado['id']}/jurados/", {"docentes": [j.pk for j in jurados]}, format="json")
    mis = cliente_de(jurados[0]).get("/api/jurado/asignaciones/").json()
    f = cliente_de(jurados[0]).get(f"/api/jurado/asignaciones/{mis[0]['id']}/formulario/").json()
    assert f["proyecto"]["estado"] == estado
    assert [c["nombre"] for c in f["criterios"]][3] != VARIANTES[("INV", "PROPUESTA")][4][0]


def test_formulario_trae_la_fecha_del_evento_activo():
    import datetime

    from evaluaciones.models import Evento

    evento = Evento.objects.filter(activo=True).first() or EventoFactory(activo=True)
    evento.fecha = datetime.date(2026, 10, 9)
    evento.nombre = "I Encuentro de Semilleros"
    evento.save()
    f = formulario("INV", "TERMINADO")
    assert f["evento"] == {"nombre": "I Encuentro de Semilleros", "fecha": "2026-10-09"}


def test_evaluacion_incluye_datos_del_evaluador_y_umbrales():
    from evaluaciones.models import Criterio
    from evaluaciones.services import registrar_evaluacion

    jurado = JuradoFactory(nombre_completo="Ana Gómez", email="ana@udenar.edu.co", departamento="Electrónica",
                           debe_cambiar_password=False)
    asignacion = AsignacionFactory(docente=jurado, proyecto=ProyectoFactory(evento=EventoFactory(activo=True)))
    autor = AutorFactory(proyecto=asignacion.proyecto)
    registrar_evaluacion(asignacion.pk, {c.pk: 2 for c in Criterio.objects.filter(tipo="INV")}, {autor.pk: True})
    e = cliente_de(jurado).get(f"/api/jurado/asignaciones/{asignacion.pk}/evaluacion/").json()
    assert e["evaluador"] == {"nombre_completo": "Ana Gómez", "departamento": "Electrónica", "email": "ana@udenar.edu.co"}
    assert e["texto_umbrales"] == TEXTO_UMBRALES
