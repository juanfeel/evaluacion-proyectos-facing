"""Permisos de la API.

Toda vista autenticada debe usar `Autenticado`, `EsAdmin` o `EsJurado`: los tres aplican RN-07.
Una vista que deba funcionar con el cambio de contraseña pendiente declara
`permite_cambio_password_pendiente = True` (solo `me` y `cambiar-password`).
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from .models import Usuario


class CambioPasswordRequerido(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Debe cambiar su contraseña antes de continuar."
    default_code = "CAMBIO_PASSWORD_REQUERIDO"


class Autenticado(BasePermission):
    message = "No tiene permiso para realizar esta acción."

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        # RN-07
        if usuario.debe_cambiar_password and not getattr(view, "permite_cambio_password_pendiente", False):
            raise CambioPasswordRequerido()
        return True


class EsAdmin(Autenticado):
    message = "Esta acción solo está disponible para el administrador."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Usuario.Rol.ADMIN


class EsJurado(Autenticado):
    message = "Esta acción solo está disponible para los jurados."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Usuario.Rol.JURADO
