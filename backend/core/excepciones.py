"""Todas las respuestas de error de la API tienen la forma {"detalle", "codigo", "campos"}."""

from django.http import Http404, JsonResponse
from rest_framework import exceptions
from rest_framework.views import exception_handler

# Códigos en español para las excepciones estándar de DRF y simplejwt.
CODIGOS = {
    "not_authenticated": "NO_AUTENTICADO",
    "authentication_failed": "AUTENTICACION_FALLIDA",
    "token_not_valid": "TOKEN_INVALIDO",
    "user_not_found": "TOKEN_INVALIDO",
    "user_inactive": "USUARIO_INACTIVO",
    "permission_denied": "PERMISO_DENEGADO",
    "not_found": "NO_ENCONTRADO",
    "method_not_allowed": "METODO_NO_PERMITIDO",
    "parse_error": "JSON_INVALIDO",
    "unsupported_media_type": "TIPO_NO_SOPORTADO",
    "not_acceptable": "NO_ACEPTABLE",
    "throttled": "DEMASIADAS_PETICIONES",
    "invalid": "DATOS_INVALIDOS",
}

MENSAJES = {
    "NO_AUTENTICADO": "Debe iniciar sesión.",
    "TOKEN_INVALIDO": "Su sesión expiró o no es válida. Inicie sesión de nuevo.",
    "NO_ENCONTRADO": "No se encontró el recurso solicitado.",
    "JSON_INVALIDO": "Los datos enviados no tienen un formato JSON válido.",
    "TIPO_NO_SOPORTADO": "Los datos deben enviarse en formato JSON.",
    "NO_ACEPTABLE": "Esta API solo responde en formato JSON.",
}


class ErrorNegocio(exceptions.APIException):
    """Violación de una regla de negocio. Por defecto 409; `codigo` identifica la regla."""

    status_code = 409
    default_code = "REGLA_DE_NEGOCIO"

    def __init__(self, detalle: str, codigo: str, status_code: int = 409):
        super().__init__(detalle, codigo)
        self.status_code = status_code


def _texto(valor) -> str:
    if isinstance(valor, (list, tuple)):
        return _texto(valor[0]) if valor else ""
    if isinstance(valor, dict):
        return _texto(next(iter(valor.values()), ""))
    return str(valor)


def _campos(detalle) -> dict:
    """Cada campo con su lista de mensajes; los anidados se conservan."""
    if not isinstance(detalle, dict):
        return {}
    campos = {}
    for clave, valor in detalle.items():
        if isinstance(valor, dict):
            campos[clave] = _campos(valor)
        elif isinstance(valor, list):
            campos[clave] = [_campos(v) if isinstance(v, dict) else str(v) for v in valor]
        else:
            campos[clave] = [str(valor)]
    return campos


def cuerpo_error(detalle: str, codigo: str, campos: dict | None = None) -> dict:
    return {"detalle": detalle, "codigo": codigo, "campos": campos or {}}


def manejador_excepciones(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    respuesta = exception_handler(exc, context)
    if respuesta is None:
        return None  # error no controlado → 500 (handler500)

    if isinstance(exc, exceptions.ValidationError):
        detalle = exc.detail
        campos = _campos(detalle) if isinstance(detalle, dict) else {}
        generales = campos.pop("non_field_errors", None) or campos.pop("detalle", None)
        codigo = getattr(exc, "codigo", None) or "DATOS_INVALIDOS"
        mensaje = _texto(generales) if generales else (
            _texto(detalle) if not campos else "Revise los datos marcados."
        )
        respuesta.data = cuerpo_error(mensaje, codigo, campos)
        return respuesta

    codigo_original = exc.get_codes() if isinstance(exc, exceptions.APIException) else None
    if isinstance(codigo_original, dict):
        codigo_original = codigo_original.get("code") or next(iter(codigo_original.values()), None)
    if isinstance(codigo_original, list):
        codigo_original = codigo_original[0] if codigo_original else None
    codigo = CODIGOS.get(codigo_original, str(codigo_original or "ERROR").upper())
    mensaje = MENSAJES.get(codigo) or _texto(getattr(exc, "detail", "")) or "Ocurrió un error."
    respuesta.data = cuerpo_error(mensaje, codigo)
    return respuesta


def no_encontrado(request, exception=None):
    return JsonResponse(cuerpo_error("No se encontró el recurso solicitado.", "NO_ENCONTRADO"), status=404)


def error_servidor(request):
    return JsonResponse(cuerpo_error("Ocurrió un error inesperado en el servidor.", "ERROR_SERVIDOR"), status=500)
