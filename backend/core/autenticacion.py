from django.http import JsonResponse

from .excepciones import cuerpo_error


def respuesta_bloqueo(request, original_response=None, credentials=None, *args, **kwargs):
    """Respuesta de django-axes cuando se supera el límite de intentos (usuario + IP)."""
    return JsonResponse(
        cuerpo_error(
            "Demasiados intentos fallidos. Por seguridad, espere 15 minutos antes de volver a intentarlo.",
            "CUENTA_BLOQUEADA",
        ),
        status=429,
    )
