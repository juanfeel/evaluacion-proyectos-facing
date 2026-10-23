from django.conf import settings
from django.db import models
from django.db.models import Q


class Origen(models.TextChoices):
    SEMILLERO = "SEMILLERO", "Semillero de investigación"
    TRABAJO_GRADO = "TRABAJO_GRADO", "Trabajo de grado"


class Tipo(models.TextChoices):
    INV = "INV", "Investigación"
    DTI = "DTI", "Desarrollo Tecnológico y/o Innovación"


class EstadoProyecto(models.TextChoices):
    PROPUESTA = "PROPUESTA", "Propuesta"
    EN_CURSO = "EN_CURSO", "En curso"
    TERMINADO = "TERMINADO", "Terminado"


class Programa(models.TextChoices):
    IS = "IS", "Ingeniería de Sistemas"
    IE = "IE", "Ingeniería Electrónica"
    IC = "IC", "Ingeniería Civil"


class Evento(models.Model):
    nombre = models.CharField(max_length=200)
    fecha = models.DateField()
    activo = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha", "nombre"]
        constraints = [
            # RN-02: solo un evento activo a la vez.
            models.UniqueConstraint(fields=["activo"], condition=Q(activo=True), name="un_solo_evento_activo"),
        ]

    def __str__(self):
        return self.nombre


class AreaConocimiento(models.Model):
    programa = models.CharField(max_length=2, choices=Programa.choices)
    nombre = models.CharField(max_length=120)

    class Meta:
        verbose_name = "área de conocimiento"
        verbose_name_plural = "áreas de conocimiento"
        ordering = ["programa", "id"]
        constraints = [
            models.UniqueConstraint(fields=["programa", "nombre"], name="area_unica_por_programa"),
        ]

    def __str__(self):
        return f"{self.get_programa_display()} · {self.nombre}"


class Proyecto(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.PROTECT, related_name="proyectos")
    codigo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=500)
    area = models.ForeignKey(AreaConocimiento, on_delete=models.PROTECT, related_name="proyectos")
    origen = models.CharField(max_length=15, choices=Origen.choices)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    estado = models.CharField(max_length=10, choices=EstadoProyecto.choices)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        constraints = [
            # RN-13
            models.UniqueConstraint(fields=["evento", "codigo"], name="codigo_unico_por_evento"),
            # RN-17
            models.CheckConstraint(
                condition=~Q(origen=Origen.TRABAJO_GRADO, estado=EstadoProyecto.PROPUESTA),
                name="trabajo_grado_no_propuesta",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.titulo}"


class Autor(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="autores")
    nombre_completo = models.CharField(max_length=200)
    cedula = models.CharField(max_length=20)
    orden = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name_plural = "autores"
        ordering = ["proyecto", "orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["proyecto", "cedula"], name="autor_unico_por_proyecto"),
        ]

    def __str__(self):
        return self.nombre_completo


class Asignacion(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name="asignaciones")
    docente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="asignaciones")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "asignación"
        verbose_name_plural = "asignaciones"
        ordering = ["proyecto", "creada", "id"]
        constraints = [
            # RN-25
            models.UniqueConstraint(fields=["proyecto", "docente"], name="docente_unico_por_proyecto"),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} → {self.docente.nombre_completo}"


class Criterio(models.Model):
    """Criterio de la rúbrica de un tipo de proyecto. Se carga por migración de datos."""

    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    orden = models.PositiveSmallIntegerField()
    # [Insuficiente, Básico, Bueno, Sobresaliente]
    puntajes = models.JSONField()

    class Meta:
        ordering = ["tipo", "orden"]
        constraints = [
            models.UniqueConstraint(fields=["tipo", "orden"], name="criterio_unico_por_tipo"),
            models.CheckConstraint(condition=Q(orden__gte=1, orden__lte=7), name="criterio_orden_1_a_7"),
        ]

    def __str__(self):
        return f"{self.tipo} · criterio {self.orden}"


class DescriptorCriterio(models.Model):
    class Estado(models.TextChoices):
        BASE = "BASE", "Base"
        PROPUESTA = "PROPUESTA", "Propuesta"
        EN_CURSO = "EN_CURSO", "En curso"

    criterio = models.ForeignKey(Criterio, on_delete=models.CASCADE, related_name="descriptores")
    estado = models.CharField(max_length=10, choices=Estado.choices)
    nombre = models.CharField(max_length=200)
    # [d0, d1, d2, d3]
    descriptores = models.JSONField()

    class Meta:
        verbose_name = "descriptor de criterio"
        verbose_name_plural = "descriptores de criterio"
        ordering = ["criterio", "estado"]
        constraints = [
            models.UniqueConstraint(fields=["criterio", "estado"], name="descriptor_unico_por_estado"),
        ]

    def __str__(self):
        return f"{self.criterio} · {self.estado} · {self.nombre}"


class Evaluacion(models.Model):
    # RN-36: una sola evaluación por asignación.
    asignacion = models.OneToOneField(Asignacion, on_delete=models.PROTECT, related_name="evaluacion")
    total = models.DecimalField(max_digits=5, decimal_places=2)
    sin_sustentacion = models.BooleanField(default=False)
    fortalezas = models.TextField(blank=True)
    aspectos_mejorar = models.TextField(blank=True)
    enviada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "evaluación"
        verbose_name_plural = "evaluaciones"
        ordering = ["enviada"]
        constraints = [
            models.CheckConstraint(condition=Q(total__gte=0, total__lte=100), name="total_entre_0_y_100"),
        ]

    def __str__(self):
        return f"Evaluación de {self.asignacion}"


class DetalleEvaluacion(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="detalles")
    criterio = models.ForeignKey(Criterio, on_delete=models.PROTECT, related_name="+")
    nivel = models.PositiveSmallIntegerField()
    # Copias (RN-39): no cambian si la rúbrica cambia después.
    puntaje = models.PositiveSmallIntegerField()
    nombre_criterio = models.CharField(max_length=200)

    class Meta:
        verbose_name = "detalle de evaluación"
        verbose_name_plural = "detalles de evaluación"
        ordering = ["evaluacion", "criterio__orden"]
        constraints = [
            models.UniqueConstraint(fields=["evaluacion", "criterio"], name="detalle_unico_por_criterio"),
            models.CheckConstraint(condition=Q(nivel__gte=0, nivel__lte=3), name="nivel_0_a_3"),
        ]


class Asistencia(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="asistencias")
    autor = models.ForeignKey(Autor, on_delete=models.PROTECT, related_name="asistencias")
    nombre_autor = models.CharField(max_length=200)  # copia
    asistio = models.BooleanField()

    class Meta:
        ordering = ["evaluacion", "autor__orden"]
        constraints = [
            models.UniqueConstraint(fields=["evaluacion", "autor"], name="asistencia_unica_por_autor"),
        ]
