"""Lógica de negocio de evaluaciones. Las vistas y serializers solo delegan aquí."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Case, CharField, Count, Prefetch, Q, Value, When
from rest_framework.exceptions import ValidationError

from core.excepciones import ErrorNegocio
from core.models import Usuario

from .models import (
    Asignacion,
    Asistencia,
    Autor,
    Criterio,
    DescriptorCriterio,
    DetalleEvaluacion,
    EstadoProyecto,
    Evaluacion,
    Evento,
    Origen,
    Proyecto,
)
from .rubricas import cargar_rubricas

MAX_JURADOS_POR_PROYECTO = 2  # RN-23
MAX_PROYECTOS_POR_DOCENTE = 3  # RN-24
MIN_AUTORES, MAX_AUTORES = 1, 5  # RN-19


class EstadoEvaluacion:
    """RN-22: estado calculado, nunca editable."""

    SIN_JURADOS = "SIN_JURADOS"
    PENDIENTE = "PENDIENTE"
    PARCIAL = "PARCIAL"
    EVALUADO = "EVALUADO"
    valores = [SIN_JURADOS, PENDIENTE, PARCIAL, EVALUADO]


def resolver_descriptor(criterio: Criterio, estado_proyecto: str) -> DescriptorCriterio:
    """Descriptor del estado del proyecto si existe; si no, el BASE.

    TERMINADO no tiene descriptores propios: siempre usa BASE.
    Usa `criterio.descriptores.all()` para aprovechar un `prefetch_related`.
    """
    por_estado = {d.estado: d for d in criterio.descriptores.all()}
    return por_estado.get(estado_proyecto) or por_estado[DescriptorCriterio.Estado.BASE]


def rubrica_resuelta(tipo: str, estado_proyecto: str) -> list[dict]:
    """Los 7 criterios del tipo, con rótulo y descriptores ajustados al estado del proyecto."""
    if estado_proyecto not in EstadoProyecto.values:
        raise ValueError(f"Estado de proyecto desconocido: {estado_proyecto}")
    criterios = Criterio.objects.filter(tipo=tipo).prefetch_related("descriptores").order_by("orden")
    resultado = []
    for criterio in criterios:
        descriptor = resolver_descriptor(criterio, estado_proyecto)
        resultado.append(
            {
                "id": criterio.id,
                "orden": criterio.orden,
                "nombre": descriptor.nombre,
                "puntajes": list(criterio.puntajes),
                "descriptores": list(descriptor.descriptores),
            }
        )
    return resultado


# ---------------------------------------------------------------- Eventos


def evento_activo() -> Evento | None:
    return Evento.objects.filter(activo=True).first()


@transaction.atomic
def crear_evento(nombre: str, fecha, activo: bool = False) -> Evento:
    evento = Evento.objects.create(nombre=nombre, fecha=fecha, activo=False)
    if activo:
        evento = activar_evento(evento.pk)
    return evento


def actualizar_evento(evento: Evento, **datos) -> Evento:
    for campo in ("nombre", "fecha"):
        if campo in datos:
            setattr(evento, campo, datos[campo])
    evento.save()
    return evento


def eliminar_evento(evento: Evento) -> None:
    if evento.proyectos.exists():
        raise ErrorNegocio("No se puede eliminar un evento que tiene proyectos.", "EVENTO_CON_PROYECTOS")
    evento.delete()


@transaction.atomic
def activar_evento(evento_id: int) -> Evento:
    """RN-02: activar uno desactiva los demás. Se bloquean todas las filas para serializar activaciones."""
    eventos = {e.pk: e for e in Evento.objects.select_for_update().order_by("pk")}
    if evento_id not in eventos:
        raise ErrorNegocio("No se encontró el evento.", "NO_ENCONTRADO", 404)
    Evento.objects.exclude(pk=evento_id).filter(activo=True).update(activo=False)
    evento = eventos[evento_id]
    if not evento.activo:
        evento.activo = True
        evento.save(update_fields=["activo"])
    return evento


# ---------------------------------------------------------------- Proyectos


def proyectos_con_estado():
    """Proyectos con su estado de evaluación (RN-22) y lo necesario para serializarlos sin N+1."""
    return (
        Proyecto.objects.select_related("evento", "area")
        .annotate(
            n_jurados=Count("asignaciones", distinct=True),
            n_evaluaciones=Count("asignaciones__evaluacion", distinct=True),
        )
        .annotate(
            estado_evaluacion=Case(
                When(n_jurados__lt=MAX_JURADOS_POR_PROYECTO, then=Value(EstadoEvaluacion.SIN_JURADOS)),
                When(n_evaluaciones=0, then=Value(EstadoEvaluacion.PENDIENTE)),
                When(n_evaluaciones__lt=MAX_JURADOS_POR_PROYECTO, then=Value(EstadoEvaluacion.PARCIAL)),
                default=Value(EstadoEvaluacion.EVALUADO),
                output_field=CharField(),
            )
        )
        .prefetch_related(
            "autores",
            Prefetch(
                "asignaciones",
                queryset=Asignacion.objects.select_related("docente", "evaluacion").order_by("creada", "id"),
            ),
        )
        .order_by("codigo", "id")
    )


def filtrar_proyectos(evento=None, origen=None, tipo=None, estado_evaluacion=None):
    errores = {}
    if origen and origen not in Origen.values:
        errores["origen"] = [f"Valor no válido: {origen}."]
    if tipo and tipo not in ("INV", "DTI"):
        errores["tipo"] = [f"Valor no válido: {tipo}."]
    if estado_evaluacion and estado_evaluacion not in EstadoEvaluacion.valores:
        errores["estado_evaluacion"] = [f"Valor no válido: {estado_evaluacion}."]
    if evento and not str(evento).isdigit():
        errores["evento"] = ["Debe ser el id numérico del evento."]
    if errores:
        raise ValidationError(errores)
    qs = proyectos_con_estado()
    if evento:
        qs = qs.filter(evento_id=int(evento))
    if origen:
        qs = qs.filter(origen=origen)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if estado_evaluacion:
        qs = qs.filter(estado_evaluacion=estado_evaluacion)
    return qs


def _validar_origen_estado(origen: str, estado: str) -> None:
    # RN-17
    if origen == Origen.TRABAJO_GRADO and estado == EstadoProyecto.PROPUESTA:
        raise ValidationError(
            {"estado": ["Un trabajo de grado no puede estar en estado Propuesta."]}
        )


def _validar_autores(autores: list[dict]) -> None:
    # RN-19
    if not MIN_AUTORES <= len(autores) <= MAX_AUTORES:
        raise ValidationError({"autores": [f"El proyecto debe tener entre {MIN_AUTORES} y {MAX_AUTORES} autores."]})
    cedulas = [a["cedula"].strip() for a in autores]
    if len(set(cedulas)) != len(cedulas):
        raise ValidationError({"autores": ["Hay autores con la misma cédula."]})


def _validar_codigo(evento_id: int, codigo: str, excluir_id: int | None = None) -> None:
    # RN-13
    qs = Proyecto.objects.filter(evento_id=evento_id, codigo__iexact=codigo.strip())
    if excluir_id:
        qs = qs.exclude(pk=excluir_id)
    if qs.exists():
        raise ValidationError({"codigo": ["Ya existe un proyecto con este código en el evento."]})


def _guardar(proyecto: Proyecto) -> None:
    try:
        with transaction.atomic():
            proyecto.save()
    except IntegrityError:
        # Carrera entre la validación y el guardado: las restricciones de la base de datos deciden.
        raise ValidationError({"codigo": ["Ya existe un proyecto con este código en el evento."]})


@transaction.atomic
def crear_proyecto(*, evento, codigo, titulo, area, origen, tipo, estado, autores) -> Proyecto:
    _validar_origen_estado(origen, estado)
    _validar_autores(autores)
    _validar_codigo(evento.pk, codigo)
    proyecto = Proyecto(
        evento=evento, codigo=codigo.strip(), titulo=titulo.strip(), area=area, origen=origen, tipo=tipo, estado=estado
    )
    _guardar(proyecto)
    for orden, autor in enumerate(autores, start=1):
        Autor.objects.create(
            proyecto=proyecto, nombre_completo=autor["nombre_completo"].strip(), cedula=autor["cedula"].strip(), orden=orden
        )
    return proyecto


def tiene_evaluaciones(proyecto: Proyecto) -> bool:
    return Evaluacion.objects.filter(asignacion__proyecto=proyecto).exists()


@transaction.atomic
def actualizar_proyecto(proyecto: Proyecto, datos: dict) -> Proyecto:
    """RN-20. Con evaluaciones enviadas solo se corrigen código, título, área y nombre/cédula de autores."""
    proyecto = Proyecto.objects.select_for_update().get(pk=proyecto.pk)
    evaluado = tiene_evaluaciones(proyecto)

    if evaluado:
        bloqueados = [
            campo for campo in ("evento", "origen", "tipo", "estado")
            if campo in datos and datos[campo] != getattr(proyecto, campo)
        ]
        if bloqueados:
            raise ErrorNegocio(
                "El proyecto ya tiene evaluaciones enviadas: no se pueden cambiar "
                + ", ".join(bloqueados) + ". Solo se pueden corregir código, título, área y datos de los autores.",
                "PROYECTO_CON_EVALUACIONES",
            )

    nuevo_evento = datos.get("evento", proyecto.evento)
    if nuevo_evento != proyecto.evento and proyecto.asignaciones.exists():
        # Protege RN-24: la carga de los jurados se cuenta por evento.
        raise ErrorNegocio(
            "Quite primero los jurados asignados para mover el proyecto a otro evento.",
            "PROYECTO_CON_JURADOS",
        )

    for campo in ("evento", "titulo", "area", "origen", "tipo", "estado", "codigo"):
        if campo in datos:
            valor = datos[campo]
            setattr(proyecto, campo, valor.strip() if isinstance(valor, str) else valor)
    _validar_origen_estado(proyecto.origen, proyecto.estado)
    _validar_codigo(proyecto.evento_id, proyecto.codigo, excluir_id=proyecto.pk)
    _guardar(proyecto)

    if "autores" in datos:
        _actualizar_autores(proyecto, datos["autores"], evaluado)
    return proyecto


def _actualizar_autores(proyecto: Proyecto, autores: list[dict], evaluado: bool) -> None:
    _validar_autores(autores)
    actuales = {a.pk: a for a in proyecto.autores.all()}
    ids_enviados = [a.get("id") for a in autores if a.get("id")]
    desconocidos = set(ids_enviados) - set(actuales)
    if desconocidos:
        raise ValidationError({"autores": ["Hay autores que no pertenecen a este proyecto."]})
    if evaluado and (len(autores) != len(actuales) or set(ids_enviados) != set(actuales)):
        raise ErrorNegocio(
            "El proyecto ya tiene evaluaciones enviadas: no se pueden agregar ni quitar autores, "
            "solo corregir su nombre o cédula.",
            "PROYECTO_CON_EVALUACIONES",
        )
    # Primero se liberan las cédulas (restricción única por proyecto) y se borran los quitados.
    Autor.objects.filter(proyecto=proyecto).exclude(pk__in=ids_enviados).delete()
    for autor in actuales.values():
        if autor.pk in ids_enviados:
            autor.cedula = f"__tmp_{autor.pk}"
            autor.save(update_fields=["cedula"])
    for orden, datos in enumerate(autores, start=1):
        campos = {"nombre_completo": datos["nombre_completo"].strip(), "cedula": datos["cedula"].strip(), "orden": orden}
        if datos.get("id"):
            Autor.objects.filter(pk=datos["id"]).update(**campos)
        else:
            Autor.objects.create(proyecto=proyecto, **campos)


@transaction.atomic
def eliminar_proyecto(proyecto: Proyecto) -> None:
    # RN-21
    if tiene_evaluaciones(proyecto):
        raise ErrorNegocio("No se puede eliminar un proyecto con evaluaciones enviadas.", "PROYECTO_CON_EVALUACIONES")
    proyecto.asignaciones.all().delete()
    proyecto.delete()


# ---------------------------------------------------------------- Asignaciones


def _bloquear_proyecto(proyecto_id: int) -> Proyecto:
    proyecto = Proyecto.objects.select_for_update().filter(pk=proyecto_id).first()
    if proyecto is None:
        raise ErrorNegocio("No se encontró el proyecto.", "NO_ENCONTRADO", 404)
    return proyecto


def _validar_cupo(docente: Usuario, evento_id: int) -> None:
    # RN-24
    carga = Asignacion.objects.filter(docente=docente, proyecto__evento_id=evento_id).count()
    if carga >= MAX_PROYECTOS_POR_DOCENTE:
        raise ErrorNegocio(
            f"{docente.nombre_completo} ya tiene {MAX_PROYECTOS_POR_DOCENTE} proyectos asignados en este evento.",
            "DOCENTE_SIN_CUPO",
        )


@transaction.atomic
def asignar_jurados(proyecto_id: int, docente_ids: list[int]) -> list[Asignacion]:
    """RN-23 a RN-27. Los 2 jurados se asignan juntos: un proyecto tiene 0 o 2 jurados, nunca 1.

    Orden fijo de bloqueo (proyecto y luego docentes por id ascendente) para evitar interbloqueos.
    """
    if len(docente_ids) != MAX_JURADOS_POR_PROYECTO or len(set(docente_ids)) != len(docente_ids):
        # RN-25
        raise ValidationError({"docentes": ["Seleccione dos docentes distintos."]})
    proyecto = _bloquear_proyecto(proyecto_id)
    docentes = list(Usuario.objects.select_for_update().filter(pk__in=docente_ids).order_by("pk"))
    if len(docentes) != len(docente_ids) or any(
        d.rol != Usuario.Rol.JURADO or not d.is_active for d in docentes
    ):
        raise ValidationError({"docentes": ["Alguno de los docentes seleccionados no existe."]})
    if Asignacion.objects.filter(proyecto=proyecto).exists():
        raise ErrorNegocio(
            f"El proyecto {proyecto.codigo} ya tiene jurados. Use «Cambiar» para reemplazar uno.", "PROYECTO_COMPLETO"
        )
    for docente in docentes:
        _validar_cupo(docente, proyecto.evento_id)
    # RN-28: no se verifican conflictos de interés en esta versión.
    por_id = {d.pk: d for d in docentes}
    # Se crean en el orden elegido por el admin: jurado 1 y jurado 2.
    return [Asignacion.objects.create(proyecto=proyecto, docente=por_id[i]) for i in docente_ids]


@transaction.atomic
def reemplazar_jurado(asignacion_id: int, nuevo_docente_id: int) -> Asignacion:
    """Cambia el docente de una asignación sin evaluación, en un solo paso (el proyecto nunca queda con 1)."""
    asignacion = Asignacion.objects.filter(pk=asignacion_id).first()
    if asignacion is None:
        raise ErrorNegocio("No se encontró la asignación.", "NO_ENCONTRADO", 404)
    proyecto = _bloquear_proyecto(asignacion.proyecto_id)
    asignacion = Asignacion.objects.select_for_update().get(pk=asignacion_id)
    if Evaluacion.objects.filter(asignacion=asignacion).exists():  # RN-26
        raise ErrorNegocio("No se puede cambiar este jurado: ya envió su evaluación.", "ASIGNACION_CON_EVALUACION")
    nuevo = Usuario.objects.select_for_update().filter(pk=nuevo_docente_id).first()
    if nuevo is None or nuevo.rol != Usuario.Rol.JURADO or not nuevo.is_active:
        raise ValidationError({"docente": ["El docente no existe."]})
    if Asignacion.objects.filter(proyecto=proyecto, docente=nuevo).exists():  # RN-25
        raise ErrorNegocio("Este docente ya es jurado de este proyecto.", "ASIGNACION_DUPLICADA")
    _validar_cupo(nuevo, proyecto.evento_id)
    asignacion.docente = nuevo
    asignacion.save(update_fields=["docente"])
    return asignacion


@transaction.atomic
def quitar_jurados(proyecto_id: int) -> None:
    """Quita los dos jurados juntos; solo si ninguno ha evaluado (RN-26)."""
    proyecto = _bloquear_proyecto(proyecto_id)
    if Evaluacion.objects.filter(asignacion__proyecto=proyecto).exists():
        raise ErrorNegocio(
            "No se pueden quitar los jurados: al menos uno ya envió su evaluación. "
            "Puede cambiar el jurado que aún no ha evaluado.",
            "ASIGNACION_CON_EVALUACION",
        )
    Asignacion.objects.filter(proyecto=proyecto).delete()


def asignaciones_de_jurado(docente: Usuario):
    """RN-03 y RN-29: solo las propias y solo del evento activo."""
    return (
        Asignacion.objects.filter(docente=docente, proyecto__evento__activo=True)
        .select_related("proyecto", "proyecto__area", "proyecto__evento", "evaluacion")
        .order_by("proyecto__codigo")
    )


# ---------------------------------------------------------------- Evaluación (jurado)

ORDEN_SUSTENTACION = 7  # RN-33
NIVEL_INSUFICIENTE = 0


def formulario(asignacion: Asignacion) -> dict:
    """RN-30: rúbrica del tipo, con textos ajustados al estado del proyecto."""
    proyecto = asignacion.proyecto
    datos = cargar_rubricas()
    return {
        "asignacion_id": asignacion.pk,
        "evaluada": hasattr(asignacion, "evaluacion"),
        # Fecha de "Datos del evaluador" mientras se llena el formulario: la del evento, como en el anexo.
        "evento": {"nombre": proyecto.evento.nombre, "fecha": proyecto.evento.fecha},
        "proyecto": proyecto,
        "autores": list(proyecto.autores.order_by("orden", "id")),
        "niveles": datos["niveles"],
        "criterios": rubrica_resuelta(proyecto.tipo, proyecto.estado),
        "nota_estado": datos["notas_estado"].get(proyecto.tipo, {}).get(proyecto.estado),
        "asistencia_alguno": datos["asistencia_alguno"],
        "asistencia_ninguno": datos["asistencia_ninguno"],
        "texto_umbrales": datos["texto_umbrales"],
    }


def _ids(diccionario: dict, campo: str) -> dict[int, object]:
    convertidos = {}
    for clave, valor in diccionario.items():
        try:
            convertidos[int(clave)] = valor
        except (TypeError, ValueError):
            raise ValidationError({campo: [f"Identificador no válido: {clave}."]})
    return convertidos


@transaction.atomic
def registrar_evaluacion(asignacion_id: int, niveles: dict, asistencia: dict, fortalezas: str = "",
                         aspectos_mejorar: str = "") -> Evaluacion:
    """RN-31 a RN-39. El total y el criterio 7 los decide el backend; la evaluación es definitiva."""
    # El bloqueo de la asignación serializa envíos dobles (RN-38).
    asignacion = Asignacion.objects.select_for_update().select_related("proyecto").get(pk=asignacion_id)
    if Evaluacion.objects.filter(asignacion=asignacion).exists():
        raise ErrorNegocio("Esta evaluación ya fue enviada y no se puede modificar.", "EVALUACION_YA_ENVIADA")
    proyecto = asignacion.proyecto

    criterios = list(
        Criterio.objects.filter(tipo=proyecto.tipo).prefetch_related("descriptores").order_by("orden")
    )
    if len(criterios) != ORDEN_SUSTENTACION:
        # La rúbrica se carga por migración; si falta, es un error de configuración, no del jurado.
        raise ErrorNegocio(
            "La rúbrica de este tipo de proyecto no está completa. Avise al administrador.", "RUBRICA_INCOMPLETA", 500
        )
    autores = list(proyecto.autores.order_by("orden", "id"))
    niveles = _ids(niveles, "niveles")
    asistencia = _ids(asistencia, "asistencia")

    errores = {}
    # RN-31: los 7 criterios, cada uno con un nivel de 0 a 3.
    faltan = [c.orden for c in criterios if c.pk not in niveles]
    sobran = set(niveles) - {c.pk for c in criterios}
    malos = [k for k, v in niveles.items() if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 3]
    if faltan:
        errores["niveles"] = [f"Falta elegir el nivel de los criterios: {', '.join(map(str, faltan))}."]
    elif sobran:
        errores["niveles"] = ["Hay criterios que no corresponden a la rúbrica de este proyecto."]
    elif malos:
        errores["niveles"] = ["Cada nivel debe ser un número entre 0 y 3."]
    # RN-32: una marca por autor.
    faltan_autores = [a.nombre_completo for a in autores if a.pk not in asistencia]
    if faltan_autores:
        errores["asistencia"] = [f"Falta marcar la asistencia de: {', '.join(faltan_autores)}."]
    elif set(asistencia) - {a.pk for a in autores}:
        errores["asistencia"] = ["Hay autores que no pertenecen a este proyecto."]
    elif any(not isinstance(v, bool) for v in asistencia.values()):
        errores["asistencia"] = ["Cada marca de asistencia debe ser verdadera o falsa."]
    if errores:
        raise ValidationError(errores)

    # RN-33: si nadie asistió, la sustentación queda en Insuficiente.
    sin_sustentacion = not any(asistencia[a.pk] for a in autores)
    if sin_sustentacion:
        for criterio in criterios:
            if criterio.orden == ORDEN_SUSTENTACION:
                niveles[criterio.pk] = NIVEL_INSUFICIENTE

    detalles = []
    for criterio in criterios:
        nivel = niveles[criterio.pk]
        detalles.append(
            DetalleEvaluacion(
                criterio=criterio,
                nivel=nivel,
                puntaje=criterio.puntajes[nivel],  # RN-39: copia
                nombre_criterio=resolver_descriptor(criterio, proyecto.estado).nombre,
            )
        )
    total = Decimal(sum(d.puntaje for d in detalles)).quantize(Decimal("0.01"))  # RN-35

    try:
        with transaction.atomic():
            evaluacion = Evaluacion.objects.create(
                asignacion=asignacion,
                total=total,
                sin_sustentacion=sin_sustentacion,
                fortalezas=(fortalezas or "").strip(),
                aspectos_mejorar=(aspectos_mejorar or "").strip(),
            )
    except IntegrityError:  # RN-36: OneToOne, por si algo se saltara el bloqueo
        raise ErrorNegocio("Esta evaluación ya fue enviada y no se puede modificar.", "EVALUACION_YA_ENVIADA")
    for detalle in detalles:
        detalle.evaluacion = evaluacion
    DetalleEvaluacion.objects.bulk_create(detalles)
    Asistencia.objects.bulk_create(
        Asistencia(evaluacion=evaluacion, autor=a, nombre_autor=a.nombre_completo, asistio=asistencia[a.pk])
        for a in autores
    )
    return evaluacion


def evaluacion_completa(evaluacion_id: int) -> Evaluacion:
    return (
        Evaluacion.objects.select_related("asignacion__proyecto__area", "asignacion__docente")
        .prefetch_related("detalles__criterio", "asistencias__autor")
        .get(pk=evaluacion_id)
    )


# ---------------------------------------------------------------- Resultados (admin)

TABLAS = [  # RN-44: cuatro tablas separadas, en este orden
    (Origen.SEMILLERO, "INV"),
    (Origen.SEMILLERO, "DTI"),
    (Origen.TRABAJO_GRADO, "INV"),
    (Origen.TRABAJO_GRADO, "DTI"),
]
DOS_DECIMALES = Decimal("0.01")


def resolver_evento(evento_id) -> Evento:
    """El evento pedido o, si no se indica, el activo."""
    if evento_id:
        if not str(evento_id).isdigit():
            raise ValidationError({"evento": ["Debe ser el id numérico del evento."]})
        evento = Evento.objects.filter(pk=int(evento_id)).first()
        if evento is None:
            raise ErrorNegocio("No se encontró el evento.", "NO_ENCONTRADO", 404)
        return evento
    evento = evento_activo()
    if evento is None:
        raise ErrorNegocio("No hay un evento activo. Indique el evento a consultar.", "SIN_EVENTO_ACTIVO", 400)
    return evento


def promedio(totales: list[Decimal]) -> Decimal:
    """RN-42: promedio de las dos evaluaciones, 2 decimales, redondeo half-up."""
    return (sum(totales, Decimal("0")) / len(totales)).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


def _fila(proyecto, umbrales) -> dict:
    evaluaciones = [a.evaluacion for a in proyecto.asignaciones.all() if hasattr(a, "evaluacion")]
    # Notas en el orden de asignación de los jurados (jurado 1, jurado 2).
    notas = [a.evaluacion.total if hasattr(a, "evaluacion") else None for a in proyecto.asignaciones.all()]
    notas = (notas + [None, None])[:2]
    completo = len(evaluaciones) >= MAX_JURADOS_POR_PROYECTO
    prom = promedio([e.total for e in evaluaciones]) if completo else None
    # RN-46: basta con que una evaluación reporte que nadie asistió (confirmado por el usuario).
    sin_sustentacion = any(e.sin_sustentacion for e in evaluaciones)
    return {
        "proyecto_id": proyecto.pk,
        "puesto": None,
        "codigo": proyecto.codigo,
        "titulo": proyecto.titulo,
        "area": proyecto.area.nombre,
        "programa": proyecto.area.get_programa_display(),
        "estado": proyecto.estado,
        "nota_jurado_1": notas[0],
        "nota_jurado_2": notas[1],
        "promedio": prom,
        "pendiente": not completo,  # RN-43
        "evaluaciones_enviadas": len(evaluaciones),
        "reconocimiento": completo and prom >= umbrales["reconocimiento"] and not sin_sustentacion,
        # Sin sustentación el proyecto "no aspira a reconocimientos" (instrucción de asistencia de la rúbrica).
        "mencion_meritoria": completo and prom >= umbrales["mencion_meritoria"] and not sin_sustentacion,
        "sin_sustentacion": sin_sustentacion,
    }


def _asignar_puestos(filas: list[dict]) -> list[dict]:
    """RN-45: de mayor a menor; los empates comparten puesto y el siguiente salta (1, 1, 3).
    RN-43: los pendientes van al final, sin puesto."""
    evaluados = sorted((f for f in filas if not f["pendiente"]), key=lambda f: (-f["promedio"], f["codigo"]))
    pendientes = sorted((f for f in filas if f["pendiente"]), key=lambda f: f["codigo"])
    anterior = None
    for indice, fila in enumerate(evaluados, start=1):
        fila["puesto"] = anterior["puesto"] if anterior and fila["promedio"] == anterior["promedio"] else indice
        anterior = fila
    return evaluados + pendientes


def calcular_resultados(evento: Evento) -> dict:
    umbrales = {k: Decimal(v) for k, v in cargar_rubricas()["umbrales"].items()}
    proyectos = list(proyectos_con_estado().filter(evento=evento))
    tablas = []
    for origen, tipo in TABLAS:
        filas = [_fila(p, umbrales) for p in proyectos if p.origen == origen and p.tipo == tipo]
        tablas.append(
            {
                "origen": origen,
                "tipo": tipo,
                "titulo": f"{Origen(origen).label} · {tipo}",
                "proyectos": _asignar_puestos(filas),
            }
        )
    return {"evento": {"id": evento.pk, "nombre": evento.nombre}, "umbrales": umbrales, "tablas": tablas}


def resumen(evento: Evento) -> dict:
    proyectos = proyectos_con_estado().filter(evento=evento)
    conteo = {estado: 0 for estado in EstadoEvaluacion.valores}
    enviadas = 0
    for p in proyectos:
        conteo[p.estado_evaluacion] += 1
        enviadas += p.n_evaluaciones
    total = sum(conteo.values())
    return {
        "evento": {"id": evento.pk, "nombre": evento.nombre, "activo": evento.activo},
        "total_proyectos": total,
        "sin_jurados": conteo[EstadoEvaluacion.SIN_JURADOS],
        "pendientes": conteo[EstadoEvaluacion.PENDIENTE],
        "parciales": conteo[EstadoEvaluacion.PARCIAL],
        "evaluados": conteo[EstadoEvaluacion.EVALUADO],
        "evaluaciones_enviadas": enviadas,
        "evaluaciones_total": total * MAX_JURADOS_POR_PROYECTO,
    }


def evaluaciones_de_proyecto(proyecto: Proyecto) -> list[Evaluacion]:
    """RN-47: ambas evaluaciones completas, en el orden de asignación de los jurados."""
    return list(
        Evaluacion.objects.filter(asignacion__proyecto=proyecto)
        .select_related("asignacion__proyecto__area", "asignacion__docente")
        .prefetch_related("detalles__criterio", "asistencias__autor")
        .order_by("asignacion__creada", "asignacion_id")
    )
