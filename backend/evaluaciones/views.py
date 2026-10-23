from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permisos import EsAdmin, EsJurado

from . import services
from .models import AreaConocimiento, Evento, Programa
from .serializers import (
    AreaSerializer,
    AsignacionJuradoSerializer,
    AsignacionSerializer,
    EvaluacionAdminSerializer,
    EvaluacionEntradaSerializer,
    EvaluacionSerializer,
    EventoEntradaSerializer,
    EventoSerializer,
    FormularioSerializer,
    JuradosEntradaSerializer,
    ProyectoEntradaSerializer,
    ProyectoSerializer,
    ReemplazoEntradaSerializer,
    ResultadosSerializer,
)


def _eventos():
    return Evento.objects.annotate(num_proyectos=Count("proyectos"))


# ---------------------------------------------------------------- Eventos


class EventosView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        return Response(EventoSerializer(_eventos(), many=True).data)

    def post(self, request):
        datos = EventoEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        evento = services.crear_evento(**datos.validated_data)
        return Response(EventoSerializer(_eventos().get(pk=evento.pk)).data, status=201)


class EventoDetalleView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request, pk):
        return Response(EventoSerializer(get_object_or_404(_eventos(), pk=pk)).data)

    def patch(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        datos = EventoEntradaSerializer(data=request.data, partial=True)
        datos.is_valid(raise_exception=True)
        datos.validated_data.pop("activo", None)  # se activa solo con /activar/
        services.actualizar_evento(evento, **datos.validated_data)
        return Response(EventoSerializer(_eventos().get(pk=pk)).data)

    def delete(self, request, pk):
        services.eliminar_evento(get_object_or_404(Evento, pk=pk))
        return Response(status=204)


class ActivarEventoView(APIView):
    permission_classes = [EsAdmin]

    def post(self, request, pk):
        evento = services.activar_evento(pk)
        return Response(EventoSerializer(_eventos().get(pk=evento.pk)).data)


# ---------------------------------------------------------------- Áreas


class AreasView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        areas = AreaConocimiento.objects.order_by("programa", "id")
        grupos = []
        for programa in Programa:
            grupos.append(
                {
                    "programa": programa.value,
                    "programa_nombre": programa.label,
                    "areas": AreaSerializer([a for a in areas if a.programa == programa.value], many=True).data,
                }
            )
        return Response(grupos)


# ---------------------------------------------------------------- Proyectos


class ProyectosView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        p = request.query_params
        qs = services.filtrar_proyectos(
            evento=p.get("evento"), origen=p.get("origen"), tipo=p.get("tipo"),
            estado_evaluacion=p.get("estado_evaluacion"),
        )
        return Response(ProyectoSerializer(qs, many=True).data)

    def post(self, request):
        datos = ProyectoEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        proyecto = services.crear_proyecto(**datos.validated_data)
        return Response(ProyectoSerializer(services.proyectos_con_estado().get(pk=proyecto.pk)).data, status=201)


class ProyectoDetalleView(APIView):
    permission_classes = [EsAdmin]

    def _proyecto(self, pk):
        return get_object_or_404(services.proyectos_con_estado(), pk=pk)

    def get(self, request, pk):
        return Response(ProyectoSerializer(self._proyecto(pk)).data)

    def patch(self, request, pk):
        proyecto = self._proyecto(pk)
        datos = ProyectoEntradaSerializer(data=request.data, partial=True)
        datos.is_valid(raise_exception=True)
        services.actualizar_proyecto(proyecto, datos.validated_data)
        return Response(ProyectoSerializer(self._proyecto(pk)).data)

    def delete(self, request, pk):
        services.eliminar_proyecto(self._proyecto(pk))
        return Response(status=204)


# ---------------------------------------------------------------- Asignaciones


class JuradosProyectoView(APIView):
    """POST asigna los dos jurados juntos; DELETE quita los dos (un proyecto tiene 0 o 2 jurados)."""

    permission_classes = [EsAdmin]

    def post(self, request, pk):
        datos = JuradosEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        asignaciones = services.asignar_jurados(pk, datos.validated_data["docentes"])
        return Response(AsignacionSerializer(asignaciones, many=True).data, status=201)

    def delete(self, request, pk):
        services.quitar_jurados(pk)
        return Response(status=204)


class AsignacionDetalleView(APIView):
    """PATCH reemplaza al jurado de una asignación sin evaluación."""

    permission_classes = [EsAdmin]

    def patch(self, request, pk):
        datos = ReemplazoEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        asignacion = services.reemplazar_jurado(pk, datos.validated_data["docente"])
        return Response(AsignacionSerializer(asignacion).data)


# ---------------------------------------------------------------- Resultados


class ResultadosView(APIView):
    permission_classes = [EsAdmin]  # RN-41

    def get(self, request):
        evento = services.resolver_evento(request.query_params.get("evento"))
        return Response(ResultadosSerializer(services.calcular_resultados(evento)).data)


class ResumenView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        evento = services.resolver_evento(request.query_params.get("evento"))
        return Response(services.resumen(evento))


class EvaluacionesProyectoView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request, pk):
        proyecto = get_object_or_404(services.proyectos_con_estado(), pk=pk)
        return Response(
            {
                "proyecto": ProyectoSerializer(proyecto).data,
                "evaluaciones": EvaluacionAdminSerializer(services.evaluaciones_de_proyecto(proyecto), many=True).data,
            }
        )


# ---------------------------------------------------------------- Jurado


def _asignacion_propia(request, pk):
    """RN-29 y RN-03: una asignación ajena o de otro evento responde 404."""
    return get_object_or_404(services.asignaciones_de_jurado(request.user), pk=pk)


class MisAsignacionesView(APIView):
    permission_classes = [EsJurado]

    def get(self, request):
        return Response(AsignacionJuradoSerializer(services.asignaciones_de_jurado(request.user), many=True).data)


class FormularioView(APIView):
    permission_classes = [EsJurado]

    def get(self, request, pk):
        return Response(FormularioSerializer(services.formulario(_asignacion_propia(request, pk))).data)


class EvaluacionView(APIView):
    """GET: evaluación propia (solo lectura). POST: envío definitivo (RN-36: no hay PUT, PATCH ni DELETE)."""

    permission_classes = [EsJurado]

    def get(self, request, pk):
        asignacion = _asignacion_propia(request, pk)
        if not hasattr(asignacion, "evaluacion"):
            return Response(
                {"detalle": "Todavía no ha enviado la evaluación de este proyecto.", "codigo": "SIN_EVALUACION", "campos": {}},
                status=404,
            )
        return Response(EvaluacionSerializer(services.evaluacion_completa(asignacion.evaluacion.pk)).data)

    def post(self, request, pk):
        asignacion = _asignacion_propia(request, pk)
        datos = EvaluacionEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        evaluacion = services.registrar_evaluacion(asignacion.pk, **datos.validated_data)
        return Response(EvaluacionSerializer(services.evaluacion_completa(evaluacion.pk)).data, status=201)
