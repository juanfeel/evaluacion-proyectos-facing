"""URLs reales + vistas de prueba para verificar permisos antes de que existan las rutas de admin/jurado."""

from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from config.urls import urlpatterns as reales
from core.permisos import Autenticado, EsAdmin, EsJurado


class _Vista(APIView):
    def get(self, request):
        return Response({"ok": True})


class VistaAutenticada(_Vista):
    permission_classes = [Autenticado]


class VistaAdmin(_Vista):
    permission_classes = [EsAdmin]


class VistaJurado(_Vista):
    permission_classes = [EsJurado]


urlpatterns = reales + [
    path("api/prueba/", VistaAutenticada.as_view()),
    path("api/admin/prueba/", VistaAdmin.as_view()),
    path("api/jurado/prueba/", VistaJurado.as_view()),
]
