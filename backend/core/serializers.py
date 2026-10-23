from rest_framework import serializers

from evaluaciones.services import MAX_PROYECTOS_POR_DOCENTE

from .models import Departamento, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Datos del usuario autenticado. No incluye la cédula."""

    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre_completo", "departamento", "rol", "debe_cambiar_password"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(trim_whitespace=False)
    password_nueva = serializers.CharField(trim_whitespace=False)
    confirmacion = serializers.CharField(trim_whitespace=False)


class DocenteSerializer(serializers.ModelSerializer):
    """Vista del administrador: incluye cédula y correo (Ley 1581: solo para el admin)."""

    asignados = serializers.IntegerField(read_only=True)
    max_asignaciones = serializers.SerializerMethodField()
    tiene_evaluaciones = serializers.BooleanField(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "nombre_completo", "cedula", "email", "departamento",
            "debe_cambiar_password", "asignados", "max_asignaciones", "tiene_evaluaciones",
        ]
        read_only_fields = fields

    def get_max_asignaciones(self, obj):
        return MAX_PROYECTOS_POR_DOCENTE


class DocenteEntradaSerializer(serializers.Serializer):
    """RN-04: nombre completo, cédula, correo institucional y departamento."""

    nombre_completo = serializers.CharField(max_length=200)
    cedula = serializers.RegexField(
        r"^\s*[0-9A-Za-z]{4,20}\s*$",
        max_length=40,
        error_messages={"invalid": "La cédula solo puede tener números o letras, sin puntos ni espacios."},
    )
    email = serializers.EmailField(max_length=254)
    departamento = serializers.ChoiceField(
        choices=Departamento.choices,
        error_messages={"invalid_choice": "Elija un departamento de la lista: Sistemas, Ingeniería Civil o Electrónica."},
    )
