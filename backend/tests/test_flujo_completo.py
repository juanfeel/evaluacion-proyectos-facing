"""Fase 4: prueba de extremo a extremo solo por API, como lo haría el frontend."""

import pytest
from rest_framework.test import APIClient

from evaluaciones.models import AreaConocimiento

from .conftest import cliente_de
from .factories import AdminFactory

pytestmark = pytest.mark.django_db


def entrar(email, password):
    client = APIClient()
    r = client.post("/api/auth/login/", {"email": email, "password": password}, format="json")
    assert r.status_code == 200, r.json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client, r.json()["usuario"]


def test_flujo_completo_por_api():
    admin = cliente_de(AdminFactory())

    # 1. Evento activo
    evento = admin.post("/api/admin/eventos/", {"nombre": "I Encuentro", "fecha": "2026-10-09"}, format="json").json()
    assert admin.post(f"/api/admin/eventos/{evento['id']}/activar/").json()["activo"] is True

    # 2. Dos docentes
    docentes = []
    for i, nombre in enumerate(["Carolina Benavides", "Andrés Erazo"], start=1):
        r = admin.post(
            "/api/admin/docentes/",
            {"nombre_completo": nombre, "cedula": f"108500000{i}", "email": f"jurado{i}@udenar.edu.co",
             "departamento": "Sistemas"},
            format="json",
        )
        assert r.status_code == 201
        docentes.append(r.json())

    # 3. Proyecto con autores
    area = AreaConocimiento.objects.get(nombre="Ciencia de datos e IA")
    proyecto = admin.post(
        "/api/admin/proyectos/",
        {"evento": evento["id"], "codigo": "IS-01", "titulo": "Predicción de deserción", "area": area.pk,
         "origen": "TRABAJO_GRADO", "tipo": "DTI", "estado": "TERMINADO",
         "autores": [{"nombre_completo": "Sofía Narváez", "cedula": "1085999001"},
                     {"nombre_completo": "Camilo Ortiz", "cedula": "1085999002"}]},
        format="json",
    ).json()
    assert proyecto["estado_evaluacion"] == "SIN_JURADOS"

    # 4. Asignar los dos jurados juntos
    assert admin.post(f"/api/admin/proyectos/{proyecto['id']}/jurados/",
                      {"docentes": [d["id"] for d in docentes]}, format="json").status_code == 201
    assert admin.get(f"/api/admin/proyectos/{proyecto['id']}/").json()["estado_evaluacion"] == "PENDIENTE"
    assert [d["asignados"] for d in admin.get("/api/admin/docentes/").json()] == [1, 1]

    # 5. Cada jurado entra con su cédula, cambia la contraseña y evalúa
    totales = []
    for i, nivel in [(1, 3), (2, 2)]:
        jurado, usuario = entrar(f"jurado{i}@udenar.edu.co", f"108500000{i}")
        assert usuario["debe_cambiar_password"] is True
        assert jurado.get("/api/jurado/asignaciones/").json()["codigo"] == "CAMBIO_PASSWORD_REQUERIDO"
        nueva = f"Evaluar-Facing-2026-{i}"
        assert jurado.post("/api/auth/cambiar-password/",
                           {"password_actual": f"108500000{i}", "password_nueva": nueva, "confirmacion": nueva},
                           format="json").status_code == 200
        jurado, _ = entrar(f"jurado{i}@udenar.edu.co", nueva)

        mis = jurado.get("/api/jurado/asignaciones/").json()
        assert len(mis) == 1 and mis[0]["evaluada"] is False
        form = jurado.get(f"/api/jurado/asignaciones/{mis[0]['id']}/formulario/").json()
        assert [c["nombre"] for c in form["criterios"]][3] == "Nivel de madurez"
        envio = {
            "niveles": {str(c["id"]): nivel for c in form["criterios"]},
            "asistencia": {str(a["id"]): True for a in form["autores"]},
            "fortalezas": "Claridad",
        }
        r = jurado.post(f"/api/jurado/asignaciones/{mis[0]['id']}/evaluacion/", envio, format="json")
        assert r.status_code == 201
        totales.append(r.json()["total"])
        # Doble envío
        assert jurado.post(f"/api/jurado/asignaciones/{mis[0]['id']}/evaluacion/", envio,
                           format="json").status_code == 409
        assert jurado.get("/api/jurado/asignaciones/").json()[0]["evaluada"] is True

        if i == 1:
            assert admin.get(f"/api/admin/proyectos/{proyecto['id']}/").json()["estado_evaluacion"] == "PARCIAL"

    assert totales == ["100.00", "67.00"]

    # 6. El admin ve el proyecto EVALUADO y ya no puede quitar jurados ni borrarlo
    final = admin.get(f"/api/admin/proyectos/{proyecto['id']}/").json()
    assert final["estado_evaluacion"] == "EVALUADO"
    assert final["evaluaciones_enviadas"] == 2
    assert admin.delete(f"/api/admin/proyectos/{proyecto['id']}/jurados/").status_code == 409
    assert admin.patch(f"/api/admin/asignaciones/{final['jurados'][0]['asignacion_id']}/",
                       {"docente": docentes[1]["id"]}, format="json").status_code == 409
    assert admin.delete(f"/api/admin/proyectos/{proyecto['id']}/").status_code == 409
    assert admin.get("/api/admin/proyectos/", {"estado_evaluacion": "EVALUADO"}).json()[0]["codigo"] == "IS-01"
