"""Fase 2: login, refresh, me, cambio de contraseña, RN-06/07/08, axes y permisos por rol."""

import datetime

import pytest
from axes.models import AccessAttempt
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from core.models import Usuario

from .factories import AdminFactory, JuradoFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/refresh/"
ME = "/api/auth/me/"
CAMBIAR = "/api/auth/cambiar-password/"
NUEVA = "Poster-Facing-2026"


def login(client, email, password, ip="10.0.0.1"):
    return client.post(LOGIN, {"email": email, "password": password}, format="json", REMOTE_ADDR=ip)


def cliente_con_token(usuario):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}")
    return client


@pytest.fixture
def admin():
    return AdminFactory(email="admin@udenar.edu.co", password="Admin-Facing-2026")


@pytest.fixture
def jurado_nuevo():
    # RN-06: contraseña inicial = cédula, debe cambiarla.
    return JuradoFactory(email="ana.perez@udenar.edu.co", cedula="1085123456")


@pytest.fixture
def jurado_activo():
    return JuradoFactory(email="luis@udenar.edu.co", cedula="1085999999", password=NUEVA, debe_cambiar_password=False)


# --- Login ---

def test_login_correcto_devuelve_tokens_y_usuario(api_client, admin):
    r = login(api_client, "admin@udenar.edu.co", "Admin-Facing-2026")
    assert r.status_code == 200
    datos = r.json()
    assert {"access", "refresh", "usuario"} <= set(datos)
    assert datos["usuario"]["rol"] == "ADMIN"
    assert datos["usuario"]["debe_cambiar_password"] is False
    assert "cedula" not in datos["usuario"]
    assert "password" not in datos["usuario"]
    admin.refresh_from_db()
    assert admin.last_login is not None


def test_login_ignora_mayusculas_y_espacios_del_correo(api_client, admin):
    assert login(api_client, "  Admin@UDENAR.edu.co ", "Admin-Facing-2026").status_code == 200


@pytest.mark.parametrize("email,password", [
    ("admin@udenar.edu.co", "incorrecta"),
    ("nadie@udenar.edu.co", "Admin-Facing-2026"),
])
def test_login_incorrecto(api_client, admin, email, password):
    r = login(api_client, email, password)
    assert r.status_code == 401
    assert r.json() == {"detalle": "Correo o contraseña incorrectos.", "codigo": "CREDENCIALES_INVALIDAS", "campos": {}}


def test_login_sin_datos_devuelve_400_con_campos(api_client):
    r = api_client.post(LOGIN, {"email": "no-es-correo"}, format="json")
    assert r.status_code == 400
    cuerpo = r.json()
    assert cuerpo["codigo"] == "DATOS_INVALIDOS"
    assert set(cuerpo["campos"]) == {"email", "password"}


def test_login_usuario_inactivo(api_client, jurado_activo):
    jurado_activo.is_active = False
    jurado_activo.save()
    assert login(api_client, "luis@udenar.edu.co", NUEVA).status_code == 401


# --- RN-06 ---

def test_rn06_docente_nuevo_entra_con_su_cedula(api_client, jurado_nuevo):
    r = login(api_client, "ana.perez@udenar.edu.co", "1085123456")
    assert r.status_code == 200
    assert r.json()["usuario"]["debe_cambiar_password"] is True
    assert r.json()["usuario"]["rol"] == "JURADO"


# --- RN-07 ---

@pytest.mark.urls("tests.urls_prueba")
@pytest.mark.parametrize("ruta", ["/api/prueba/", "/api/jurado/prueba/", "/api/admin/prueba/"])
def test_rn07_bloquea_rutas_protegidas(jurado_nuevo, ruta):
    r = cliente_con_token(jurado_nuevo).get(ruta)
    assert r.status_code == 403
    assert r.json()["codigo"] == "CAMBIO_PASSWORD_REQUERIDO"


def test_rn07_permite_me(jurado_nuevo):
    r = cliente_con_token(jurado_nuevo).get(ME)
    assert r.status_code == 200
    assert r.json()["debe_cambiar_password"] is True


def test_rn07_permite_refresh(api_client, jurado_nuevo):
    refresh = login(api_client, "ana.perez@udenar.edu.co", "1085123456").json()["refresh"]
    assert api_client.post(REFRESH, {"refresh": refresh}, format="json").status_code == 200


def _rutas(patrones, prefijo=""):
    for patron in patrones:
        if isinstance(patron, URLResolver):
            yield from _rutas(patron.url_patterns, prefijo + str(patron.pattern))
        elif isinstance(patron, URLPattern):
            yield prefijo + str(patron.pattern), patron


def test_rn07_cubre_todas_las_rutas_reales_de_la_api(jurado_nuevo):
    """Cualquier ruta /api/ nueva queda bloqueada con el cambio de contraseña pendiente."""
    permitidas = {"api/health/", "api/auth/login/", "api/auth/refresh/", "api/auth/me/", "api/auth/cambiar-password/"}
    client = cliente_con_token(jurado_nuevo)
    revisadas = 0
    for ruta, patron in _rutas(get_resolver().url_patterns):
        if not ruta.startswith("api/") or ruta in permitidas:
            continue
        url = "/" + ruta.replace("<int:pk>", "1").replace("<int:id>", "1")
        assert "<" not in url, f"Agregar el parámetro de {ruta} a esta prueba"
        r = client.get(url)
        assert r.status_code == 403 and r.json()["codigo"] == "CAMBIO_PASSWORD_REQUERIDO", ruta
        revisadas += 1
    assert revisadas >= 10  # rutas de admin desde la fase 3


# --- RN-08 y cambio de contraseña ---

def cambiar(client, actual, nueva, confirmacion=None):
    return client.post(
        CAMBIAR,
        {"password_actual": actual, "password_nueva": nueva, "confirmacion": nueva if confirmacion is None else confirmacion},
        format="json",
    )


@pytest.mark.parametrize("nueva,motivo", [
    ("1085123456", "cédula"),
    ("12345678", "solo numérica"),
    ("password", "común"),
    ("Ab1-x", "corta"),
    ("ana.perez@udenar", "parecida al correo"),
])
def test_rn08_rechaza_contrasenas_no_validas(jurado_nuevo, nueva, motivo):
    r = cambiar(cliente_con_token(jurado_nuevo), "1085123456", nueva)
    assert r.status_code == 400, motivo
    assert r.json()["codigo"] == "DATOS_INVALIDOS"
    assert "password_nueva" in r.json()["campos"]
    jurado_nuevo.refresh_from_db()
    assert jurado_nuevo.debe_cambiar_password is True


def test_rn08_mensaje_especifico_para_la_cedula(jurado_nuevo):
    r = cambiar(cliente_con_token(jurado_nuevo), "1085123456", "1085123456")
    assert "La nueva contraseña no puede ser igual a su cédula." in r.json()["campos"]["password_nueva"]


def test_cambio_rechaza_password_actual_incorrecta(jurado_nuevo):
    r = cambiar(cliente_con_token(jurado_nuevo), "otra", NUEVA)
    assert r.status_code == 400
    assert "password_actual" in r.json()["campos"]


def test_cambio_rechaza_confirmacion_distinta(jurado_nuevo):
    r = cambiar(cliente_con_token(jurado_nuevo), "1085123456", NUEVA, "Otra-Distinta-2026")
    assert r.status_code == 400
    assert "confirmacion" in r.json()["campos"]


@pytest.mark.urls("tests.urls_prueba")
def test_tras_cambiar_la_contrasena_el_acceso_es_normal(api_client, jurado_nuevo):
    client = cliente_con_token(jurado_nuevo)
    r = cambiar(client, "1085123456", NUEVA)
    assert r.status_code == 200
    assert r.json()["debe_cambiar_password"] is False

    jurado_nuevo.refresh_from_db()
    assert jurado_nuevo.debe_cambiar_password is False
    assert client.get("/api/jurado/prueba/").status_code == 200
    assert login(api_client, "ana.perez@udenar.edu.co", "1085123456").status_code == 401
    assert login(api_client, "ana.perez@udenar.edu.co", NUEVA).status_code == 200


def test_cambiar_password_requiere_autenticacion(api_client):
    r = cambiar(api_client, "a", NUEVA)
    assert r.status_code == 401
    assert r.json()["codigo"] == "NO_AUTENTICADO"


# --- Tokens ---

def test_duracion_de_los_tokens(api_client, admin):
    datos = login(api_client, "admin@udenar.edu.co", "Admin-Facing-2026").json()
    access, refresh = AccessToken(datos["access"]), RefreshToken(datos["refresh"])
    assert access["exp"] - access["iat"] == 30 * 60
    assert refresh["exp"] - refresh["iat"] == 12 * 3600


def test_refresh_rota_y_el_anterior_queda_invalido(api_client, admin):
    refresh = login(api_client, "admin@udenar.edu.co", "Admin-Facing-2026").json()["refresh"]
    r = api_client.post(REFRESH, {"refresh": refresh}, format="json")
    assert r.status_code == 200
    assert r.json()["refresh"] != refresh
    assert "access" in r.json()
    reuso = api_client.post(REFRESH, {"refresh": refresh}, format="json")
    assert reuso.status_code == 401
    assert reuso.json()["codigo"] == "TOKEN_INVALIDO"


def test_access_expirado_devuelve_401_token_invalido(admin):
    token = AccessToken.for_user(admin)
    token.set_exp(lifetime=-datetime.timedelta(seconds=1))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    r = client.get(ME)
    assert r.status_code == 401
    assert r.json()["codigo"] == "TOKEN_INVALIDO"


def test_me_sin_token(api_client):
    r = api_client.get(ME)
    assert r.status_code == 401
    assert r.json() == {"detalle": "Debe iniciar sesión.", "codigo": "NO_AUTENTICADO", "campos": {}}


# --- django-axes ---

def test_bloqueo_tras_5_intentos_fallidos(api_client, jurado_activo):
    for intento in range(4):
        assert login(api_client, "luis@udenar.edu.co", "mala").status_code == 401, intento
    quinto = login(api_client, "luis@udenar.edu.co", "mala")
    assert quinto.status_code == 429
    # Bloqueado: ni con la contraseña correcta entra desde esa IP.
    r = login(api_client, "luis@udenar.edu.co", NUEVA)
    assert r.status_code == 429
    assert r.json()["codigo"] == "CUENTA_BLOQUEADA"


def test_bloqueo_es_por_usuario_mas_ip(api_client, jurado_activo):
    for _ in range(5):
        login(api_client, "luis@udenar.edu.co", "mala", ip="10.0.0.66")
    # Mismo usuario desde otra IP (el jurado real): no está bloqueado.
    assert login(api_client, "luis@udenar.edu.co", NUEVA, ip="10.0.0.2").status_code == 200


def test_bloqueo_expira_a_los_15_minutos(api_client, jurado_activo):
    for _ in range(5):
        login(api_client, "luis@udenar.edu.co", "mala")
    assert login(api_client, "luis@udenar.edu.co", NUEVA).status_code == 429
    hace_16_min = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=16)
    AccessAttempt.objects.update(attempt_time=hace_16_min)
    assert login(api_client, "luis@udenar.edu.co", NUEVA).status_code == 200


def test_login_correcto_reinicia_los_fallos(api_client, jurado_activo):
    for _ in range(4):
        login(api_client, "luis@udenar.edu.co", "mala")
    assert login(api_client, "luis@udenar.edu.co", NUEVA).status_code == 200
    for _ in range(4):
        assert login(api_client, "luis@udenar.edu.co", "mala").status_code == 401


# --- Permisos por rol ---

@pytest.mark.urls("tests.urls_prueba")
def test_jurado_recibe_403_en_rutas_de_admin(jurado_activo):
    r = cliente_con_token(jurado_activo).get("/api/admin/prueba/")
    assert r.status_code == 403
    assert r.json()["codigo"] == "PERMISO_DENEGADO"


@pytest.mark.urls("tests.urls_prueba")
def test_admin_accede_a_admin_y_no_a_jurado(admin):
    client = cliente_con_token(admin)
    assert client.get("/api/admin/prueba/").status_code == 200
    assert client.get("/api/jurado/prueba/").status_code == 403


@pytest.mark.urls("tests.urls_prueba")
def test_sin_token_rutas_de_admin_devuelven_401(api_client):
    assert api_client.get("/api/admin/prueba/").status_code == 401


def test_json_malformado_responde_en_espanol(api_client):
    r = api_client.post(LOGIN, "{malformado", content_type="application/json")
    assert r.status_code == 400
    assert r.json() == {"detalle": "Los datos enviados no tienen un formato JSON válido.", "codigo": "JSON_INVALIDO", "campos": {}}


def test_ruta_inexistente_devuelve_404_json(api_client):
    r = api_client.get("/api/no-existe/")
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"
