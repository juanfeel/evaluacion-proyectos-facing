import pytest
from django.db import connection


@pytest.mark.django_db
def test_health_responde_ok_con_db(api_client):
    respuesta = api_client.get("/api/health/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "db": True}


@pytest.mark.django_db
def test_health_reporta_db_caida(api_client, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(connection, "cursor", falla)
    respuesta = api_client.get("/api/health/")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"ok": True, "db": False}


def test_health_es_json_puro(api_client, db):
    respuesta = api_client.get("/api/health/")
    assert respuesta["Content-Type"].startswith("application/json")
