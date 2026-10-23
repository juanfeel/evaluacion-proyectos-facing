import pytest
from django.core.management import CommandError, call_command

from core.models import Usuario

pytestmark = pytest.mark.django_db


def _contrasenas(monkeypatch, *valores):
    respuestas = iter(valores)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(respuestas))


def test_crea_administrador(monkeypatch):
    _contrasenas(monkeypatch, "Facing-Admin-2026", "Facing-Admin-2026")
    call_command("crear_admin", email="Admin@Udenar.edu.co", nombre="Coordinación FACING")
    admin = Usuario.objects.get(email="admin@udenar.edu.co")
    assert admin.rol == Usuario.Rol.ADMIN
    assert admin.debe_cambiar_password is False
    assert admin.check_password("Facing-Admin-2026")
    assert admin.cedula is None


def test_pide_datos_por_consola(monkeypatch):
    entradas = iter(["coord@udenar.edu.co", "Coordinación"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(entradas))
    _contrasenas(monkeypatch, "Facing-Admin-2026", "Facing-Admin-2026")
    call_command("crear_admin")
    assert Usuario.objects.filter(email="coord@udenar.edu.co", rol="ADMIN").exists()


def test_rechaza_contrasenas_distintas(monkeypatch):
    _contrasenas(monkeypatch, "Facing-Admin-2026", "Otra-Cosa-2026")
    with pytest.raises(CommandError, match="no coinciden"):
        call_command("crear_admin", email="a@udenar.edu.co", nombre="A")
    assert not Usuario.objects.exists()


def test_rechaza_contrasena_debil(monkeypatch):
    _contrasenas(monkeypatch, "12345678", "12345678")
    with pytest.raises(CommandError, match="Contraseña no válida"):
        call_command("crear_admin", email="a@udenar.edu.co", nombre="A")


def test_rechaza_correo_repetido(monkeypatch):
    Usuario.objects.create_superuser(email="a@udenar.edu.co", password="x", nombre_completo="A")
    with pytest.raises(CommandError, match="Ya existe"):
        call_command("crear_admin", email="a@udenar.edu.co", nombre="A")
