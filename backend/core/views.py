from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from . import services
from .permisos import Autenticado, EsAdmin
from .serializers import (
    CambiarPasswordSerializer,
    DocenteEntradaSerializer,
    DocenteSerializer,
    LoginSerializer,
    UsuarioSerializer,
)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Verifica que la API responde y que la base de datos es alcanzable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Exception:
        db_ok = False
    return Response({"ok": True, "db": db_ok}, status=200 if db_ok else 503)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        # Se pasa el HttpRequest original: django-axes marca en él el bloqueo.
        usuario, tokens = services.iniciar_sesion(
            request._request, datos.validated_data["email"], datos.validated_data["password"]
        )
        if usuario is None:
            # Bloqueado por axes: AxesMiddleware reemplaza esta respuesta por la de bloqueo (429).
            return Response(status=429)
        return Response({**tokens, "usuario": UsuarioSerializer(usuario).data})


class RefreshView(TokenRefreshView):
    """Rota el refresh token (el anterior queda en la lista negra)."""


class MeView(APIView):
    permission_classes = [Autenticado]
    permite_cambio_password_pendiente = True

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class CambiarPasswordView(APIView):
    permission_classes = [Autenticado]
    permite_cambio_password_pendiente = True

    def post(self, request):
        datos = CambiarPasswordSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        v = datos.validated_data
        usuario = services.cambiar_password(
            request.user, v["password_actual"], v["password_nueva"], v["confirmacion"]
        )
        return Response(UsuarioSerializer(usuario).data)


# ---------------------------------------------------------------- Administración de docentes


class DocentesView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        qs = services.docentes_con_carga()
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nombre_completo__icontains=q) | Q(cedula__icontains=q)
                | Q(email__icontains=q) | Q(departamento__icontains=q)
            )
        return Response(DocenteSerializer(qs, many=True).data)

    def post(self, request):
        datos = DocenteEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        docente = services.crear_docente(**datos.validated_data)
        return Response(DocenteSerializer(services.docentes_con_carga().get(pk=docente.pk)).data, status=201)


class DocenteDetalleView(APIView):
    permission_classes = [EsAdmin]

    def _docente(self, pk):
        return get_object_or_404(services.docentes_con_carga(), pk=pk)

    def get(self, request, pk):
        return Response(DocenteSerializer(self._docente(pk)).data)

    def patch(self, request, pk):
        docente = self._docente(pk)
        datos = DocenteEntradaSerializer(data=request.data, partial=True)
        datos.is_valid(raise_exception=True)
        services.actualizar_docente(docente, **datos.validated_data)
        return Response(DocenteSerializer(self._docente(pk)).data)

    def delete(self, request, pk):
        services.eliminar_docente(self._docente(pk))
        return Response(status=204)


class RestablecerPasswordView(APIView):
    permission_classes = [EsAdmin]

    def post(self, request, pk):
        docente = get_object_or_404(services.docentes_con_carga(), pk=pk)
        services.restablecer_password(docente)
        return Response(
            {"detalle": "La contraseña volvió a ser la cédula del docente. Deberá cambiarla al iniciar sesión."}
        )
