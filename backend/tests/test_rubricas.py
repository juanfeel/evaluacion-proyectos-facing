"""Pruebas obligatorias sobre la rúbrica (CLAUDE.md, sección 6) y resolución de descriptores."""

import re
from pathlib import Path

import pytest
import yaml

from evaluaciones.models import Criterio, DescriptorCriterio, EstadoProyecto
from evaluaciones.rubricas import RUTA_RUBRICAS, cargar_rubricas
from evaluaciones.services import rubrica_resuelta

pytestmark = pytest.mark.django_db

TIPOS = ["INV", "DTI"]
ESTADOS = EstadoProyecto.values  # PROPUESTA, EN_CURSO, TERMINADO


def test_yaml_es_identico_al_de_claude_md():
    claude_md = (Path(__file__).resolve().parents[2] / "CLAUDE.md").read_text(encoding="utf-8")
    bloque = re.search(r"```yaml\n(.*?)```", claude_md, re.S).group(1)
    assert RUTA_RUBRICAS.read_text(encoding="utf-8") == bloque


@pytest.mark.parametrize("tipo", TIPOS)
def test_cada_tipo_tiene_7_criterios_con_4_puntajes_y_4_descriptores(tipo):
    criterios = Criterio.objects.filter(tipo=tipo).prefetch_related("descriptores")
    assert sorted(c.orden for c in criterios) == [1, 2, 3, 4, 5, 6, 7]
    for criterio in criterios:
        assert len(criterio.puntajes) == 4
        assert criterio.puntajes == sorted(criterio.puntajes)
        estados = {d.estado for d in criterio.descriptores.all()}
        assert "BASE" in estados
        for descriptor in criterio.descriptores.all():
            assert len(descriptor.descriptores) == 4
            assert all(texto.strip() for texto in descriptor.descriptores)
            assert descriptor.nombre.strip()


@pytest.mark.parametrize("tipo", TIPOS)
@pytest.mark.parametrize("estado", ESTADOS)
def test_suma_maxima_100_y_minima_0_por_tipo_y_estado(tipo, estado):
    rubrica = rubrica_resuelta(tipo, estado)
    assert len(rubrica) == 7
    assert sum(c["puntajes"][3] for c in rubrica) == 100
    assert sum(c["puntajes"][0] for c in rubrica) == 0
    assert all(len(c["descriptores"]) == 4 for c in rubrica)


def test_puntajes_identicos_entre_inv_y_dti():
    inv = {c.orden: c.puntajes for c in Criterio.objects.filter(tipo="INV")}
    dti = {c.orden: c.puntajes for c in Criterio.objects.filter(tipo="DTI")}
    assert inv == dti


def test_base_de_datos_coincide_con_el_yaml():
    datos = cargar_rubricas()
    for tipo in TIPOS:
        for item in datos[tipo]:
            criterio = Criterio.objects.get(tipo=tipo, orden=item["orden"])
            assert criterio.puntajes == item["puntajes"]
            esperados = {e: item[e] for e in ("BASE", "PROPUESTA", "EN_CURSO") if e in item}
            en_db = {d.estado: d for d in criterio.descriptores.all()}
            assert set(en_db) == set(esperados)
            for estado, contenido in esperados.items():
                assert en_db[estado].nombre == contenido["nombre"]
                assert en_db[estado].descriptores == contenido["descriptores"]
    assert Criterio.objects.count() == 14


def test_niveles_y_umbrales_del_yaml():
    datos = cargar_rubricas()
    assert datos["niveles"] == ["Insuficiente", "Básico", "Bueno", "Sobresaliente"]
    assert datos["umbrales"] == {"reconocimiento": 80, "mencion_meritoria": 85}
    assert set(datos["notas_estado"]) == {"INV", "DTI"}
    assert datos["asistencia_alguno"].startswith("Si al menos un ponente se presentó")
    assert datos["asistencia_ninguno"].startswith("Si ningún ponente se presentó")
    assert datos["texto_umbrales"] == "Umbral de reconocimiento: 80 puntos. Mención meritoria: 85 puntos."


# --- Resolución de descriptores (BASE / PROPUESTA / EN_CURSO) ---

NOMBRES_ESPERADOS = {
    # (tipo, estado): rótulos de los criterios 1..7
    ("INV", "TERMINADO"): [
        "Planteamiento del problema, objetivos y pertinencia",
        "Antecedentes",
        "Rigor metodológico",
        "Resultados y avances",
        "Conclusiones y trabajo futuro",
        "Calidad del póster",
        "Sustentación",
    ],
    ("INV", "PROPUESTA"): [
        "Planteamiento del problema, objetivos y pertinencia",
        "Antecedentes",
        "Rigor metodológico",
        "Resultados esperados y viabilidad",
        "Aportes previstos y trabajo futuro",
        "Calidad del póster",
        "Sustentación",
    ],
    ("INV", "EN_CURSO"): [
        "Planteamiento del problema, objetivos y pertinencia",
        "Antecedentes",
        "Diseño en ejecución",
        "Avances obtenidos hasta la fecha",
        "Conclusiones y trabajo futuro",
        "Calidad del póster",
        "Sustentación",
    ],
    ("DTI", "TERMINADO"): [
        "Reto tecnológico, objetivos y pertinencia",
        "Soluciones existentes y grado de novedad",
        "Enfoque técnico",
        "Nivel de madurez",
        "Aplicabilidad y transferencia",
        "Calidad del póster",
        "Sustentación",
    ],
    ("DTI", "PROPUESTA"): [
        "Reto tecnológico, objetivos y pertinencia",
        "Soluciones existentes y grado de novedad",
        "Enfoque técnico",
        "Madurez esperada y viabilidad",
        "Aplicabilidad prevista y trabajo futuro",
        "Calidad del póster",
        "Sustentación",
    ],
    ("DTI", "EN_CURSO"): [
        "Reto tecnológico, objetivos y pertinencia",
        "Soluciones existentes y grado de novedad",
        "Enfoque en desarrollo, no el desarrollo concluido",
        "Madurez alcanzada a la fecha, no el desarrollo concluido",
        "Aplicabilidad y transferencia",
        "Calidad del póster",
        "Sustentación",
    ],
}


@pytest.mark.parametrize("tipo,estado", list(NOMBRES_ESPERADOS))
def test_resolucion_de_rotulos_por_tipo_y_estado(tipo, estado):
    rubrica = rubrica_resuelta(tipo, estado)
    assert [c["nombre"] for c in rubrica] == NOMBRES_ESPERADOS[(tipo, estado)]
    assert [c["orden"] for c in rubrica] == [1, 2, 3, 4, 5, 6, 7]


def test_descriptores_de_propuesta_reemplazan_a_base():
    rubrica = rubrica_resuelta("DTI", "PROPUESTA")
    assert rubrica[3]["descriptores"][0] == "Sin plan de desarrollo ni madurez esperada"
    assert rubrica[4]["descriptores"][3] == "Aplicación prevista con ruta de continuidad definida"
    # Criterio sin descriptor PROPUESTA usa BASE.
    assert rubrica[2]["descriptores"][2] == "Arquitectura completa y coherente con el reto"


def test_terminado_usa_siempre_base():
    base = {
        d.criterio.orden: d.descriptores
        for d in DescriptorCriterio.objects.filter(criterio__tipo="INV", estado="BASE").select_related("criterio")
    }
    rubrica = rubrica_resuelta("INV", "TERMINADO")
    assert {c["orden"]: c["descriptores"] for c in rubrica} == base


def test_estado_desconocido_falla():
    with pytest.raises(ValueError):
        rubrica_resuelta("INV", "BASE")
