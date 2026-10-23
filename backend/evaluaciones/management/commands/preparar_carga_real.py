from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from core.models import Usuario
from evaluaciones.models import Asignacion, Asistencia, Autor, DetalleEvaluacion, Evaluacion, Evento, Proyecto


class Command(BaseCommand):
    help = (
        "Borra los datos de prueba (eventos, proyectos, autores, asignaciones, evaluaciones, jurados y registros "
        "de acceso) y deja la base lista para la carga real. Conserva administradores, áreas y rúbrica. "
        "Sin --confirmar solo muestra lo que borraría."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true", help="Borra de verdad (sin esto, solo simula).")

    def handle(self, *args, confirmar=False, **opciones):
        conteos = {
            "Eventos": Evento.objects.count(),
            "Proyectos": Proyecto.objects.count(),
            "Autores": Autor.objects.count(),
            "Asignaciones": Asignacion.objects.count(),
            "Evaluaciones": Evaluacion.objects.count(),
            "Detalles de evaluación": DetalleEvaluacion.objects.count(),
            "Asistencias": Asistencia.objects.count(),
            "Jurados (docentes)": Usuario.objects.filter(rol=Usuario.Rol.JURADO).count(),
            "Registros de acceso (axes)": AccessAttempt.objects.count() + AccessFailureLog.objects.count() + AccessLog.objects.count(),
            "Tokens de sesión": OutstandingToken.objects.count(),
        }
        self.stdout.write("Se borrarían:" if not confirmar else "Borrando:")
        for nombre, cantidad in conteos.items():
            self.stdout.write(f"  {nombre}: {cantidad}")
        admins = list(Usuario.objects.filter(rol=Usuario.Rol.ADMIN).values_list("email", flat=True))
        self.stdout.write(f"Se conservan: administradores {admins}, áreas de conocimiento y rúbrica.")
        if not confirmar:
            self.stdout.write(self.style.WARNING("Simulación: no se borró nada. Repita con --confirmar para borrar."))
            return
        with transaction.atomic():
            # Orden por las restricciones PROTECT: evaluaciones → asignaciones → proyectos → eventos → jurados.
            Evaluacion.objects.all().delete()
            Asignacion.objects.all().delete()
            Proyecto.objects.all().delete()
            Evento.objects.all().delete()
            BlacklistedToken.objects.all().delete()
            OutstandingToken.objects.all().delete()
            Usuario.objects.filter(rol=Usuario.Rol.JURADO).delete()
            for modelo in (AccessAttempt, AccessFailureLog, AccessLog):
                modelo.objects.all().delete()
            Session.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Listo: la base quedó vacía para la carga real."))
