"""RN-27: asignaciones simultáneas no rompen RN-23 ni RN-24 (requiere PostgreSQL real)."""

import threading

import pytest
from django.db import connection, connections

from core.excepciones import ErrorNegocio
from evaluaciones.models import Asignacion, Criterio, DetalleEvaluacion, Evaluacion
from evaluaciones.services import activar_evento, asignar_jurados, reemplazar_jurado, registrar_evaluacion

from .factories import AsignacionFactory, AutorFactory, EventoFactory, JuradoFactory, ProyectoFactory

pytestmark = [
    # serialized_rollback: estas pruebas vacían las tablas al terminar; así se restauran áreas y rúbricas.
    pytest.mark.django_db(transaction=True, serialized_rollback=True),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="select_for_update requiere PostgreSQL"),
]


def en_paralelo(funciones):
    """Lanza todas las funciones a la vez (barrera) y devuelve cuántas tuvieron éxito y los errores."""
    barrera = threading.Barrier(len(funciones))
    exitos, errores = [], []
    candado = threading.Lock()

    def correr(funcion):
        try:
            barrera.wait()
            funcion()
            with candado:
                exitos.append(1)
        except ErrorNegocio as error:
            with candado:
                errores.append(error.get_codes())
        except Exception as error:  # cualquier otro error es un fallo de la prueba
            with candado:
                errores.append(repr(error))
        finally:
            connections.close_all()

    hilos = [threading.Thread(target=correr, args=(f,)) for f in funciones]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return len(exitos), errores


def test_docente_no_queda_con_4_proyectos():
    evento = EventoFactory()
    docente = JuradoFactory()
    proyectos = [ProyectoFactory(evento=evento) for _ in range(8)]
    companeros = [JuradoFactory() for _ in range(8)]
    exitos, errores = en_paralelo(
        [lambda p=p, c=c: asignar_jurados(p.pk, [docente.pk, c.pk]) for p, c in zip(proyectos, companeros)]
    )
    assert exitos == 3
    assert errores == ["DOCENTE_SIN_CUPO"] * 5
    assert Asignacion.objects.filter(docente=docente).count() == 3
    # Todo o nada: ningún proyecto quedó con un solo jurado.
    for p in proyectos:
        assert Asignacion.objects.filter(proyecto=p).count() in (0, 2)


def test_proyecto_no_queda_con_mas_de_2_jurados():
    proyecto = ProyectoFactory()
    parejas = [(JuradoFactory(), JuradoFactory()) for _ in range(6)]
    exitos, errores = en_paralelo([lambda a=a, b=b: asignar_jurados(proyecto.pk, [a.pk, b.pk]) for a, b in parejas])
    assert exitos == 1
    assert errores == ["PROYECTO_COMPLETO"] * 5
    assert Asignacion.objects.filter(proyecto=proyecto).count() == 2


def test_reemplazos_simultaneos_respetan_el_cupo():
    evento = EventoFactory()
    docente = JuradoFactory()
    asignar_jurados(ProyectoFactory(evento=evento).pk, [docente.pk, JuradoFactory().pk])  # le quedan 2 cupos
    asignaciones = [asignar_jurados(ProyectoFactory(evento=evento).pk, [JuradoFactory().pk, JuradoFactory().pk])[0]
                    for _ in range(6)]
    exitos, errores = en_paralelo([lambda a=a: reemplazar_jurado(a.pk, docente.pk) for a in asignaciones])
    assert exitos == 2
    assert errores == ["DOCENTE_SIN_CUPO"] * 4
    assert Asignacion.objects.filter(docente=docente).count() == 3


def test_cruzado_proyectos_y_docentes_sin_interbloqueo():
    """Muchas parejas a la vez sobre los mismos proyectos y docentes: se respetan los límites y nadie se bloquea."""
    evento = EventoFactory()
    proyectos = [ProyectoFactory(evento=evento) for _ in range(4)]
    docentes = [JuradoFactory() for _ in range(4)]
    parejas = [(a, b) for i, a in enumerate(docentes) for b in docentes[i + 1:]]  # 6 parejas
    tareas = [lambda p=p, a=a, b=b: asignar_jurados(p.pk, [b.pk, a.pk]) for p in proyectos for a, b in parejas]
    exitos, errores = en_paralelo(tareas)
    assert all(e in ("PROYECTO_COMPLETO", "DOCENTE_SIN_CUPO") for e in errores), errores
    for p in proyectos:
        assert Asignacion.objects.filter(proyecto=p).count() in (0, 2)
    for d in docentes:
        assert Asignacion.objects.filter(docente=d).count() <= 3
    assert exitos == 4 and Asignacion.objects.count() == 8


def test_activaciones_simultaneas_dejan_un_solo_evento_activo():
    eventos = [EventoFactory() for _ in range(5)]
    exitos, errores = en_paralelo([lambda e=e: activar_evento(e.pk) for e in eventos])
    assert errores == []
    assert exitos == 5
    from evaluaciones.models import Evento

    assert Evento.objects.filter(activo=True).count() == 1


def test_rn38_envios_simultaneos_crean_una_sola_evaluacion():
    """Doble toque / reintento de red: varios POST a la vez."""
    asignacion = AsignacionFactory()
    autor = AutorFactory(proyecto=asignacion.proyecto)
    niveles = {c.pk: 3 for c in Criterio.objects.filter(tipo=asignacion.proyecto.tipo)}
    exitos, errores = en_paralelo(
        [lambda: registrar_evaluacion(asignacion.pk, dict(niveles), {autor.pk: True}) for _ in range(6)]
    )
    assert exitos == 1
    assert errores == ["EVALUACION_YA_ENVIADA"] * 5
    assert Evaluacion.objects.count() == 1
    assert DetalleEvaluacion.objects.count() == 7
