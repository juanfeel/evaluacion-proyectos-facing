import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from core.models import Usuario


class Command(BaseCommand):
    help = "Crea un usuario administrador. Pide correo, nombre completo y contraseña."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Correo del administrador")
        parser.add_argument("--nombre", help="Nombre completo del administrador")

    def handle(self, *args, **opciones):
        email = (opciones.get("email") or input("Correo: ")).strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError("El correo no es válido.")
        if Usuario.objects.filter(email=email).exists():
            raise CommandError("Ya existe un usuario con ese correo.")

        nombre = (opciones.get("nombre") or input("Nombre completo: ")).strip()
        if not nombre:
            raise CommandError("El nombre es obligatorio.")

        password = getpass.getpass("Contraseña: ")
        if password != getpass.getpass("Repita la contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")
        candidato = Usuario(email=email, nombre_completo=nombre, rol=Usuario.Rol.ADMIN)
        try:
            validate_password(password, user=candidato)
        except ValidationError as error:
            raise CommandError("Contraseña no válida: " + " ".join(error.messages))

        Usuario.objects.create_superuser(email=email, password=password, nombre_completo=nombre)
        self.stdout.write(self.style.SUCCESS(f"Administrador {email} creado."))
