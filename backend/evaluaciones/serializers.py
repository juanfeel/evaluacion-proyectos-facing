from rest_framework import serializers

from .models import AreaConocimiento, Asignacion, Autor, EstadoProyecto, Evento, Origen, Proyecto, Tipo
from .rubricas import cargar_rubricas

# ---------------------------------------------------------------- Eventos


class EventoSerializer(serializers.ModelSerializer):
    num_proyectos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Evento
        fields = ["id", "nombre", "fecha", "activo", "num_proyectos"]
        read_only_fields = ["id", "activo", "num_proyectos"]


class EventoEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=200)
    fecha = serializers.DateField()
    activo = serializers.BooleanField(required=False, default=False)


# ---------------------------------------------------------------- Áreas


class AreaSerializer(serializers.ModelSerializer):
    programa_nombre = serializers.CharField(source="get_programa_display", read_only=True)

    class Meta:
        model = AreaConocimiento
        fields = ["id", "nombre", "programa", "programa_nombre"]


# ---------------------------------------------------------------- Proyectos


class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ["id", "nombre_completo", "cedula", "orden"]


class JuradoAsignadoSerializer(serializers.ModelSerializer):
    asignacion_id = serializers.IntegerField(source="id")
    docente_id = serializers.IntegerField(source="docente.id")
    nombre_completo = serializers.CharField(source="docente.nombre_completo")
    evaluada = serializers.SerializerMethodField()

    class Meta:
        model = Asignacion
        fields = ["asignacion_id", "docente_id", "nombre_completo", "evaluada"]

    def get_evaluada(self, obj):
        return hasattr(obj, "evaluacion")


class ProyectoSerializer(serializers.ModelSerializer):
    """Salida para el admin. Requiere un queryset de `services.proyectos_con_estado()`."""

    area = AreaSerializer(read_only=True)
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True)
    origen_nombre = serializers.CharField(source="get_origen_display", read_only=True)
    tipo_nombre = serializers.CharField(source="get_tipo_display", read_only=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    autores = AutorSerializer(many=True, read_only=True)
    jurados = JuradoAsignadoSerializer(source="asignaciones", many=True, read_only=True)
    estado_evaluacion = serializers.CharField(read_only=True)
    evaluaciones_enviadas = serializers.IntegerField(source="n_evaluaciones", read_only=True)
    tiene_evaluaciones = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = [
            "id", "evento", "evento_nombre", "codigo", "titulo", "area",
            "origen", "origen_nombre", "tipo", "tipo_nombre", "estado", "estado_nombre",
            "autores", "jurados", "estado_evaluacion", "evaluaciones_enviadas", "tiene_evaluaciones",
            "creado", "actualizado",
        ]

    def get_tiene_evaluaciones(self, obj):
        # RN-20: el frontend bloquea campos con esta marca.
        return obj.n_evaluaciones > 0


class AutorEntradaSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    nombre_completo = serializers.CharField(max_length=200)
    cedula = serializers.RegexField(
        r"^\s*[0-9A-Za-z]{4,20}\s*$",
        max_length=40,
        error_messages={"invalid": "La cédula solo puede tener números o letras, sin puntos ni espacios."},
    )


class ProyectoEntradaSerializer(serializers.Serializer):
    evento = serializers.PrimaryKeyRelatedField(queryset=Evento.objects.all())  # RN-01
    codigo = serializers.CharField(max_length=50)
    titulo = serializers.CharField(max_length=500)
    area = serializers.PrimaryKeyRelatedField(queryset=AreaConocimiento.objects.all())
    origen = serializers.ChoiceField(choices=Origen.choices)
    tipo = serializers.ChoiceField(choices=Tipo.choices)
    estado = serializers.ChoiceField(choices=EstadoProyecto.choices)
    autores = AutorEntradaSerializer(many=True, allow_empty=True)


# ---------------------------------------------------------------- Asignaciones


class JuradosEntradaSerializer(serializers.Serializer):
    """Los dos jurados de un proyecto, en orden (jurado 1, jurado 2)."""

    docentes = serializers.ListField(child=serializers.IntegerField(), min_length=2, max_length=2,
                                     error_messages={"min_length": "Seleccione los dos jurados.",
                                                     "max_length": "Seleccione solo dos jurados."})


class ReemplazoEntradaSerializer(serializers.Serializer):
    docente = serializers.IntegerField()


class AsignacionSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.CharField(source="docente.nombre_completo", read_only=True)

    class Meta:
        model = Asignacion
        fields = ["id", "proyecto", "docente", "docente_nombre", "creada"]


# ---------------------------------------------------------------- Jurado
# RN-40 y Ley 1581: nada de estas salidas incluye cédulas, correos ni datos del otro jurado.


class ProyectoJuradoSerializer(serializers.ModelSerializer):
    origen_nombre = serializers.CharField(source="get_origen_display")
    tipo_nombre = serializers.CharField(source="get_tipo_display")
    estado_nombre = serializers.CharField(source="get_estado_display")
    area = serializers.CharField(source="area.nombre")
    programa = serializers.CharField(source="area.get_programa_display")

    class Meta:
        model = Proyecto
        fields = [
            "codigo", "titulo", "origen", "origen_nombre", "tipo", "tipo_nombre",
            "estado", "estado_nombre", "area", "programa",
        ]


class AsignacionJuradoSerializer(serializers.ModelSerializer):
    proyecto = ProyectoJuradoSerializer()
    evaluada = serializers.SerializerMethodField()
    enviada = serializers.SerializerMethodField()

    class Meta:
        model = Asignacion
        fields = ["id", "proyecto", "evaluada", "enviada"]

    def get_evaluada(self, obj):
        return hasattr(obj, "evaluacion")

    def get_enviada(self, obj):
        return obj.evaluacion.enviada if hasattr(obj, "evaluacion") else None


class AutorJuradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ["id", "nombre_completo", "orden"]


class CriterioFormularioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    orden = serializers.IntegerField()
    nombre = serializers.CharField()
    puntajes = serializers.ListField(child=serializers.IntegerField())
    descriptores = serializers.ListField(child=serializers.CharField())


class EventoFormularioSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    fecha = serializers.DateField()


class FormularioSerializer(serializers.Serializer):
    asignacion_id = serializers.IntegerField()
    evaluada = serializers.BooleanField()
    evento = EventoFormularioSerializer()
    proyecto = ProyectoJuradoSerializer()
    autores = AutorJuradoSerializer(many=True)
    niveles = serializers.ListField(child=serializers.CharField())
    criterios = CriterioFormularioSerializer(many=True)
    nota_estado = serializers.CharField(allow_null=True)
    asistencia_alguno = serializers.CharField()
    asistencia_ninguno = serializers.CharField()
    texto_umbrales = serializers.CharField()


class EvaluacionEntradaSerializer(serializers.Serializer):
    """Cualquier otro campo (p. ej. `total`) se ignora: RN-35."""

    niveles = serializers.DictField(child=serializers.JSONField())
    asistencia = serializers.DictField(child=serializers.JSONField())
    fortalezas = serializers.CharField(required=False, allow_blank=True, max_length=3000, default="")
    aspectos_mejorar = serializers.CharField(required=False, allow_blank=True, max_length=3000, default="")


class DetalleEvaluacionSerializer(serializers.Serializer):
    criterio_id = serializers.IntegerField(source="criterio.id")
    orden = serializers.IntegerField(source="criterio.orden")
    nombre_criterio = serializers.CharField()
    nivel = serializers.IntegerField()
    nivel_nombre = serializers.SerializerMethodField()
    puntaje = serializers.IntegerField()
    puntaje_maximo = serializers.SerializerMethodField()

    def get_nivel_nombre(self, obj):
        return cargar_rubricas()["niveles"][obj.nivel]

    def get_puntaje_maximo(self, obj):
        return obj.criterio.puntajes[-1]


class AsistenciaSerializer(serializers.Serializer):
    autor_id = serializers.IntegerField(source="autor.id")
    nombre_autor = serializers.CharField()
    asistio = serializers.BooleanField()


class EvaluadorSerializer(serializers.Serializer):
    """Datos del evaluador: reemplazan la firma del formato físico."""

    nombre_completo = serializers.CharField()
    departamento = serializers.CharField()
    email = serializers.EmailField()


class EvaluacionSerializer(serializers.Serializer):
    """Evaluación propia, solo lectura."""

    id = serializers.IntegerField()
    asignacion_id = serializers.IntegerField(source="asignacion.id")
    proyecto = ProyectoJuradoSerializer(source="asignacion.proyecto")
    total = serializers.DecimalField(max_digits=5, decimal_places=2)
    sin_sustentacion = serializers.BooleanField()
    fortalezas = serializers.CharField()
    aspectos_mejorar = serializers.CharField()
    enviada = serializers.DateTimeField()
    detalles = serializers.SerializerMethodField()
    asistencias = serializers.SerializerMethodField()
    evaluador = EvaluadorSerializer(source="asignacion.docente")
    texto_umbrales = serializers.SerializerMethodField()

    def get_texto_umbrales(self, obj):
        return cargar_rubricas()["texto_umbrales"]

    def get_detalles(self, obj):
        detalles = sorted(obj.detalles.all(), key=lambda d: d.criterio.orden)
        return DetalleEvaluacionSerializer(detalles, many=True).data

    def get_asistencias(self, obj):
        asistencias = sorted(obj.asistencias.all(), key=lambda a: (a.autor.orden, a.autor_id))
        return AsistenciaSerializer(asistencias, many=True).data


# ---------------------------------------------------------------- Resultados (admin)


def _nota(**kwargs):
    return serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True, **kwargs)


class FilaResultadoSerializer(serializers.Serializer):
    proyecto_id = serializers.IntegerField()
    puesto = serializers.IntegerField(allow_null=True)
    codigo = serializers.CharField()
    titulo = serializers.CharField()
    area = serializers.CharField()
    programa = serializers.CharField()
    estado = serializers.CharField()
    nota_jurado_1 = _nota()
    nota_jurado_2 = _nota()
    promedio = _nota()
    pendiente = serializers.BooleanField()
    evaluaciones_enviadas = serializers.IntegerField()
    reconocimiento = serializers.BooleanField()
    mencion_meritoria = serializers.BooleanField()
    sin_sustentacion = serializers.BooleanField()


class TablaResultadosSerializer(serializers.Serializer):
    origen = serializers.CharField()
    tipo = serializers.CharField()
    titulo = serializers.CharField()
    proyectos = FilaResultadoSerializer(many=True)


class ResultadosSerializer(serializers.Serializer):
    evento = serializers.DictField()
    umbrales = serializers.DictField(child=serializers.DecimalField(max_digits=5, decimal_places=2))
    tablas = TablaResultadosSerializer(many=True)


class JuradoEvaluadorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre_completo = serializers.CharField()
    departamento = serializers.CharField()
    email = serializers.EmailField()


class EvaluacionAdminSerializer(EvaluacionSerializer):
    """RN-47: evaluación completa con el jurado que la hizo (solo para el admin)."""

    jurado = JuradoEvaluadorSerializer(source="asignacion.docente")
