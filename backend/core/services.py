"""Lógica de negocio de usuarios y autenticación."""

from axes.utils import reset as reiniciar_intentos_axes
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.contrib.auth.signals import user_logged_in
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from evaluaciones.models import Asignacion, Evaluacion

from .excepciones import ErrorNegocio
from .models import Usuario


class CredencialesInvalidas(APIException):
    # APIException (no AuthenticationFailed): DRF convertiría esta última en 403
    # porque la vista de login no tiene clases de autenticación.
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Correo o contraseña incorrectos."
    default_code = "CREDENCIALES_INVALIDAS"


def iniciar_sesion(http_request, email: str, password: str) -> tuple[Usuario | None, dict | None]:
    """Autentica por correo pasando por django-axes.

    Devuelve (usuario, tokens). Si axes bloqueó la petición devuelve (None, None) y
    deja `http_request.axes_locked_out = True` para que el middleware responda 429.
    """
    usuario = authenticate(http_request, email=email.strip().lower(), password=password)
    if getattr(http_request, "axes_locked_out", False):
        return None, None
    if usuario is None:
        raise CredencialesInvalidas()
    # Actualiza last_login y hace que django-axes reinicie los intentos fallidos.
    user_logged_in.send(sender=usuario.__class__, request=http_request, user=usuario)
    refresh = RefreshToken.for_user(usuario)
    return usuario, {"access": str(refresh.access_token), "refresh": str(refresh)}


def validar_password_nueva(usuario: Usuario, password: str) -> None:
    """RN-08: validadores de Django y distinta de la cédula."""
    errores = []
    try:
        validate_password(password, user=usuario)
    except DjangoValidationError as error:
        errores.extend(error.messages)
    if usuario.cedula and password.strip() == usuario.cedula.strip():
        errores.append("La nueva contraseña no puede ser igual a su cédula.")
    if errores:
        raise ValidationError({"password_nueva": errores})


def cambiar_password(usuario: Usuario, actual: str, nueva: str, confirmacion: str) -> Usuario:
    if not usuario.check_password(actual):
        raise ValidationError({"password_actual": ["La contraseña actual no es correcta."]})
    if nueva != confirmacion:
        raise ValidationError({"confirmacion": ["La confirmación no coincide con la nueva contraseña."]})
    validar_password_nueva(usuario, nueva)
    if nueva == actual:
        raise ValidationError({"password_nueva": ["La nueva contraseña debe ser distinta de la actual."]})
    usuario.set_password(nueva)
    usuario.debe_cambiar_password = False
    usuario.save(update_fields=["password", "debe_cambiar_password"])
    return usuario


# ---------------------------------------------------------------- Docentes (administración)


def docentes_con_carga():
    """Jurados con su carga de proyectos en el evento activo (asignados/3)."""
    return (
        Usuario.objects.filter(rol=Usuario.Rol.JURADO)
        .annotate(
            asignados=Count("asignaciones", filter=Q(asignaciones__proyecto__evento__activo=True), distinct=True),
            tiene_evaluaciones=Exists(Evaluacion.objects.filter(asignacion__docente=OuterRef("pk"))),
        )
        .order_by("nombre_completo", "id")
    )


def _validar_unicos(email: str | None, cedula: str | None, excluir_id: int | None = None) -> None:
    errores = {}
    otros = Usuario.objects.exclude(pk=excluir_id) if excluir_id else Usuario.objects.all()
    if email is not None and otros.filter(email__iexact=email.strip()).exists():
        errores["email"] = ["Ya existe un usuario con este correo."]
    if cedula is not None and otros.filter(cedula=cedula.strip()).exists():
        errores["cedula"] = ["Ya existe un docente con esta cédula."]
    if errores:
        raise ValidationError(errores)


def crear_docente(*, nombre_completo: str, cedula: str, email: str, departamento: str) -> Usuario:
    """RN-04 a RN-06: la contraseña inicial es la cédula y debe cambiarla al entrar."""
    _validar_unicos(email, cedula)
    try:
        with transaction.atomic():
            return Usuario.objects.create_user(
                email=email,
                password=cedula.strip(),
                nombre_completo=nombre_completo.strip(),
                cedula=cedula.strip(),
                departamento=departamento.strip(),
                rol=Usuario.Rol.JURADO,
                debe_cambiar_password=True,
            )
    except IntegrityError:
        _validar_unicos(email, cedula)
        raise


def actualizar_docente(docente: Usuario, **datos) -> Usuario:
    """RN-10: cambiar la cédula no cambia la contraseña."""
    _validar_unicos(datos.get("email"), datos.get("cedula"), excluir_id=docente.pk)
    for campo in ("nombre_completo", "cedula", "email", "departamento"):
        if campo in datos:
            setattr(docente, campo, datos[campo].strip())
    docente.save()
    return docente


def eliminar_docente(docente: Usuario) -> None:
    """RN-11. Si tiene asignaciones, primero hay que reemplazarlo: un proyecto nunca queda con un solo jurado."""
    with transaction.atomic():
        if Evaluacion.objects.filter(asignacion__docente=docente).exists():
            raise ErrorNegocio(
                "No se puede eliminar un docente que ya envió evaluaciones.", "DOCENTE_CON_EVALUACIONES"
            )
        if Asignacion.objects.filter(docente=docente).exists():
            raise ErrorNegocio(
                "Este docente es jurado de algún proyecto. Reemplácelo o quite los jurados de esos proyectos "
                "antes de eliminarlo.",
                "DOCENTE_CON_ASIGNACIONES",
            )
        docente.delete()


def restablecer_password(docente: Usuario) -> Usuario:
    """RN-09: vuelve a la cédula, exige cambiarla y levanta el bloqueo de django-axes del docente."""
    docente.set_password(docente.cedula)
    docente.debe_cambiar_password = True
    docente.save(update_fields=["password", "debe_cambiar_password"])
    reiniciar_intentos_axes(username=docente.email)
    return docente
