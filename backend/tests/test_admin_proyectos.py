"""Fase 3: proyectos (RN-12, RN-13, RN-17 a RN-22) y asignaciones (RN-23 a RN-26)."""

import pytest

from evaluaciones.models import AreaConocimiento, Asignacion, Autor, Proyecto

from .factories import (
    AsignacionFactory,
    AutorFactory,
    EvaluacionFactory,
    EventoFactory,
    JuradoFactory,
    ProyectoFactory,
)

pytestmark = pytest.mark.django_db

PROYECTOS = "/api/admin/proyectos/"
ASIGNACIONES = "/api/admin/asignaciones/"


def autores(n):
    return [{"nombre_completo": f"Estudiante {i}", "cedula": f"10850000{i:02d}"} for i in range(1, n + 1)]


@pytest.fixture
def evento():
    return EventoFactory(activo=True)


@pytest.fixture
def area():
    return AreaConocimiento.objects.get(nombre="Geotecnia")


@pytest.fixture
def datos(evento, area):
    return {
        "evento": evento.pk,
        "codigo": "IC-01",
        "titulo": "Estabilidad de taludes en la vía Pasto–Tumaco",
        "area": area.pk,
        "origen": "SEMILLERO",
        "tipo": "INV",
        "estado": "EN_CURSO",
        "autores": autores(2),
    }


# ---------------------------------------------------------------- Crear (RN-12, RN-13, RN-17, RN-18, RN-19)


def test_rn12_crear_proyecto_con_autores(admin_client, datos):
    r = admin_client.post(PROYECTOS, datos, format="json")
    assert r.status_code == 201, r.json()
    p = r.json()
    assert p["codigo"] == "IC-01"
    assert p["area"] == {
        "id": datos["area"], "nombre": "Geotecnia", "programa": "IC", "programa_nombre": "Ingeniería Civil"
    }  # RN-18: programa derivado del área
    assert [a["nombre_completo"] for a in p["autores"]] == ["Estudiante 1", "Estudiante 2"]
    assert [a["orden"] for a in p["autores"]] == [1, 2]
    assert p["estado_evaluacion"] == "SIN_JURADOS"
    assert p["jurados"] == [] and p["tiene_evaluaciones"] is False


def test_rn01_proyecto_requiere_evento(admin_client, datos):
    datos.pop("evento")
    r = admin_client.post(PROYECTOS, datos, format="json")
    assert r.status_code == 400
    assert "evento" in r.json()["campos"]


@pytest.mark.parametrize("n", [1, 5])
def test_rn19_entre_1_y_5_autores_validos(admin_client, datos, n):
    datos["autores"] = autores(n)
    assert admin_client.post(PROYECTOS, datos, format="json").status_code == 201


@pytest.mark.parametrize("n", [0, 6])
def test_rn19_rechaza_0_o_6_autores(admin_client, datos, n):
    datos["autores"] = autores(n)
    r = admin_client.post(PROYECTOS, datos, format="json")
    assert r.status_code == 400
    assert "autores" in r.json()["campos"]
    assert not Proyecto.objects.exists()


def test_rn19_autor_requiere_nombre_y_cedula(admin_client, datos):
    datos["autores"] = [{"nombre_completo": "", "cedula": ""}]
    r = admin_client.post(PROYECTOS, datos, format="json")
    assert r.status_code == 400
    assert set(r.json()["campos"]["autores"]["0"]) == {"nombre_completo", "cedula"}  # por índice de fila


def test_autores_con_cedula_repetida(admin_client, datos):
    datos["autores"] = [{"nombre_completo": "A", "cedula": "12345"}, {"nombre_completo": "B", "cedula": "12345"}]
    r = admin_client.post(PROYECTOS, datos, format="json")
    assert r.status_code == 400
    assert not Proyecto.objects.exists()


def test_rn13_codigo_unico_en_el_evento(admin_client, datos):
    admin_client.post(PROYECTOS, datos, format="json")
    r = admin_client.post(PROYECTOS, {**datos, "codigo": "ic-01 "}, format="json")
    assert r.status_code == 400
    assert "codigo" in r.json()["campos"]
    otro = EventoFactory()
    assert admin_client.post(PROYECTOS, {**datos, "evento": otro.pk}, format="json").status_code == 201


def test_rn17_trabajo_de_grado_en_propuesta(admin_client, datos):
    r = admin_client.post(PROYECTOS, {**datos, "origen": "TRABAJO_GRADO", "estado": "PROPUESTA"}, format="json")
    assert r.status_code == 400
    assert r.json()["campos"] == {"estado": ["Un trabajo de grado no puede estar en estado Propuesta."]}


def test_valores_no_validos_de_origen_tipo_estado(admin_client, datos):
    r = admin_client.post(PROYECTOS, {**datos, "origen": "X", "tipo": "Y", "estado": "Z"}, format="json")
    assert r.status_code == 400
    assert set(r.json()["campos"]) == {"origen", "tipo", "estado"}


# ---------------------------------------------------------------- Listado y filtros


def test_filtros_del_listado(admin_client, evento):
    otro = EventoFactory()
    ProyectoFactory(evento=evento, codigo="A", origen="SEMILLERO", tipo="INV")
    ProyectoFactory(evento=evento, codigo="B", origen="TRABAJO_GRADO", tipo="DTI")
    completo = ProyectoFactory(evento=evento, codigo="C", origen="SEMILLERO", tipo="DTI")
    AsignacionFactory(proyecto=completo)
    AsignacionFactory(proyecto=completo)
    ProyectoFactory(evento=otro, codigo="D")

    def codigos(**filtros):
        r = admin_client.get(PROYECTOS, filtros)
        assert r.status_code == 200
        return [p["codigo"] for p in r.json()]

    assert codigos() == ["A", "B", "C", "D"]
    assert codigos(evento=evento.pk) == ["A", "B", "C"]
    assert codigos(evento=evento.pk, origen="SEMILLERO") == ["A", "C"]
    assert codigos(evento=evento.pk, tipo="DTI") == ["B", "C"]
    assert codigos(evento=evento.pk, estado_evaluacion="PENDIENTE") == ["C"]
    assert codigos(evento=evento.pk, estado_evaluacion="SIN_JURADOS") == ["A", "B"]
    assert codigos(origen="SEMILLERO", tipo="DTI", estado_evaluacion="PENDIENTE") == ["C"]


def test_filtros_con_valores_no_validos(admin_client):
    r = admin_client.get(PROYECTOS, {"origen": "OTRO", "estado_evaluacion": "X", "evento": "abc"})
    assert r.status_code == 400
    assert set(r.json()["campos"]) == {"origen", "estado_evaluacion", "evento"}


def test_listado_sin_consultas_n_mas_1(admin_client, evento, django_assert_max_num_queries):
    for _ in range(10):
        p = ProyectoFactory(evento=evento)
        AutorFactory(proyecto=p)
        EvaluacionFactory(asignacion=AsignacionFactory(proyecto=p))
    with django_assert_max_num_queries(8):
        assert len(admin_client.get(PROYECTOS).json()) == 10


# ---------------------------------------------------------------- RN-22


def test_rn22_estado_de_evaluacion_en_los_4_casos(admin_client):
    p = ProyectoFactory()

    def estado():
        return admin_client.get(f"{PROYECTOS}{p.pk}/").json()["estado_evaluacion"]

    assert estado() == "SIN_JURADOS"
    a1 = AsignacionFactory(proyecto=p)
    assert estado() == "SIN_JURADOS"  # 1 de 2
    a2 = AsignacionFactory(proyecto=p)
    assert estado() == "PENDIENTE"
    EvaluacionFactory(asignacion=a1)
    assert estado() == "PARCIAL"
    EvaluacionFactory(asignacion=a2)
    assert estado() == "EVALUADO"
    detalle = admin_client.get(f"{PROYECTOS}{p.pk}/").json()
    assert detalle["evaluaciones_enviadas"] == 2
    assert [j["evaluada"] for j in detalle["jurados"]] == [True, True]


def test_rn22_estado_no_es_editable(admin_client):
    p = ProyectoFactory()
    admin_client.patch(f"{PROYECTOS}{p.pk}/", {"estado_evaluacion": "EVALUADO"}, format="json")
    assert admin_client.get(f"{PROYECTOS}{p.pk}/").json()["estado_evaluacion"] == "SIN_JURADOS"


# ---------------------------------------------------------------- Editar (RN-20)


def test_editar_proyecto_sin_evaluaciones(admin_client):
    p = ProyectoFactory(tipo="INV", estado="EN_CURSO")
    a1, a2 = AutorFactory(proyecto=p, cedula="111111"), AutorFactory(proyecto=p, cedula="222222")
    r = admin_client.patch(
        f"{PROYECTOS}{p.pk}/",
        {
            "tipo": "DTI",
            "estado": "PROPUESTA",
            "autores": [
                {"id": a2.pk, "nombre_completo": "Segundo ahora primero", "cedula": "222222"},
                {"nombre_completo": "Nuevo", "cedula": "333333"},
            ],
        },
        format="json",
    )
    assert r.status_code == 200, r.json()
    assert (r.json()["tipo"], r.json()["estado"]) == ("DTI", "PROPUESTA")
    assert [(a["cedula"], a["orden"]) for a in r.json()["autores"]] == [("222222", 1), ("333333", 2)]
    assert not Autor.objects.filter(pk=a1.pk).exists()


def test_intercambiar_cedulas_entre_autores(admin_client):
    p = ProyectoFactory()
    a1, a2 = AutorFactory(proyecto=p, cedula="111111"), AutorFactory(proyecto=p, cedula="222222")
    r = admin_client.patch(
        f"{PROYECTOS}{p.pk}/",
        {"autores": [{"id": a1.pk, "nombre_completo": "A", "cedula": "222222"},
                     {"id": a2.pk, "nombre_completo": "B", "cedula": "111111"}]},
        format="json",
    )
    assert r.status_code == 200, r.json()


def test_rn17_tambien_al_editar(admin_client):
    p = ProyectoFactory(origen="SEMILLERO", estado="PROPUESTA")
    r = admin_client.patch(f"{PROYECTOS}{p.pk}/", {"origen": "TRABAJO_GRADO"}, format="json")
    assert r.status_code == 400
    assert "estado" in r.json()["campos"]


def test_rn13_al_editar(admin_client):
    p1 = ProyectoFactory(codigo="X-1")
    p2 = ProyectoFactory(codigo="X-2", evento=p1.evento)
    r = admin_client.patch(f"{PROYECTOS}{p2.pk}/", {"codigo": "X-1"}, format="json")
    assert r.status_code == 400


@pytest.fixture
def evaluado():
    p = ProyectoFactory(tipo="INV", estado="EN_CURSO", origen="SEMILLERO")
    AutorFactory(proyecto=p, cedula="111111")
    AutorFactory(proyecto=p, cedula="222222")
    EvaluacionFactory(asignacion=AsignacionFactory(proyecto=p))
    return p


@pytest.mark.parametrize("campo,valor", [("tipo", "DTI"), ("estado", "TERMINADO"), ("origen", "TRABAJO_GRADO")])
def test_rn20_con_evaluaciones_no_cambia_tipo_estado_origen(admin_client, evaluado, campo, valor):
    r = admin_client.patch(f"{PROYECTOS}{evaluado.pk}/", {campo: valor}, format="json")
    assert r.status_code == 409
    assert r.json()["codigo"] == "PROYECTO_CON_EVALUACIONES"
    evaluado.refresh_from_db()
    assert getattr(evaluado, campo) != valor


def test_rn20_con_evaluaciones_no_cambia_evento(admin_client, evaluado):
    r = admin_client.patch(f"{PROYECTOS}{evaluado.pk}/", {"evento": EventoFactory().pk}, format="json")
    assert r.status_code == 409


def test_rn20_enviar_el_mismo_valor_no_es_un_cambio(admin_client, evaluado):
    r = admin_client.patch(f"{PROYECTOS}{evaluado.pk}/", {"tipo": "INV", "titulo": "Nuevo"}, format="json")
    assert r.status_code == 200


def test_rn20_con_evaluaciones_si_corrige_codigo_titulo_area_y_autores(admin_client, evaluado):
    a1, a2 = evaluado.autores.all()
    area = AreaConocimiento.objects.get(nombre="RV/RA")
    r = admin_client.patch(
        f"{PROYECTOS}{evaluado.pk}/",
        {
            "codigo": "NUEVO-1",
            "titulo": "Título corregido",
            "area": area.pk,
            "autores": [
                {"id": a1.pk, "nombre_completo": "Nombre corregido", "cedula": "111119"},
                {"id": a2.pk, "nombre_completo": a2.nombre_completo, "cedula": "222222"},
            ],
        },
        format="json",
    )
    assert r.status_code == 200, r.json()
    assert r.json()["codigo"] == "NUEVO-1"
    assert r.json()["area"]["nombre"] == "RV/RA"
    assert r.json()["autores"][0] == {"id": a1.pk, "nombre_completo": "Nombre corregido", "cedula": "111119", "orden": 1}


@pytest.mark.parametrize("cambio", ["agregar", "quitar"])
def test_rn20_con_evaluaciones_no_agrega_ni_quita_autores(admin_client, evaluado, cambio):
    a1, a2 = evaluado.autores.all()
    lista = [{"id": a1.pk, "nombre_completo": "A", "cedula": "111111"}]
    if cambio == "agregar":
        lista += [{"id": a2.pk, "nombre_completo": "B", "cedula": "222222"}, {"nombre_completo": "C", "cedula": "333333"}]
    r = admin_client.patch(f"{PROYECTOS}{evaluado.pk}/", {"autores": lista}, format="json")
    assert r.status_code == 409
    assert evaluado.autores.count() == 2


def test_autor_de_otro_proyecto_es_rechazado(admin_client):
    p = ProyectoFactory()
    ajeno = AutorFactory()
    r = admin_client.patch(
        f"{PROYECTOS}{p.pk}/", {"autores": [{"id": ajeno.pk, "nombre_completo": "X", "cedula": "99999"}]}, format="json"
    )
    assert r.status_code == 400
    ajeno.refresh_from_db()
    assert ajeno.proyecto != p


def test_mover_a_otro_evento_con_jurados_asignados(admin_client):
    asignacion = AsignacionFactory()
    r = admin_client.patch(f"{PROYECTOS}{asignacion.proyecto.pk}/", {"evento": EventoFactory().pk}, format="json")
    assert r.status_code == 409
    assert r.json()["codigo"] == "PROYECTO_CON_JURADOS"


# ---------------------------------------------------------------- Eliminar (RN-21)


def test_eliminar_proyecto_sin_evaluaciones(admin_client):
    asignacion = AsignacionFactory()
    AutorFactory(proyecto=asignacion.proyecto)
    assert admin_client.delete(f"{PROYECTOS}{asignacion.proyecto.pk}/").status_code == 204
    assert not Proyecto.objects.exists() and not Autor.objects.exists() and not Asignacion.objects.exists()


def test_rn21_no_se_elimina_proyecto_con_evaluaciones(admin_client, evaluado):
    r = admin_client.delete(f"{PROYECTOS}{evaluado.pk}/")
    assert r.status_code == 409
    assert Proyecto.objects.filter(pk=evaluado.pk).exists()


def test_proyecto_inexistente(admin_client):
    assert admin_client.get(f"{PROYECTOS}999/").json()["codigo"] == "NO_ENCONTRADO"


# ---------------------------------------------------------------- Asignaciones (RN-23 a RN-26)
# Un proyecto tiene 0 o 2 jurados: se asignan juntos, se reemplazan de a uno y se quitan juntos.


def asignar(client, proyecto, *docentes):
    return client.post(f"{PROYECTOS}{proyecto.pk}/jurados/", {"docentes": [d.pk for d in docentes]}, format="json")


def reemplazar(client, asignacion_id, docente):
    return client.patch(f"{ASIGNACIONES}{asignacion_id}/", {"docente": docente.pk}, format="json")


def test_asignar_los_dos_jurados_juntos(admin_client):
    p = ProyectoFactory()
    r = asignar(admin_client, p, JuradoFactory(nombre_completo="Ana"), JuradoFactory(nombre_completo="Luis"))
    assert r.status_code == 201
    assert [a["docente_nombre"] for a in r.json()] == ["Ana", "Luis"]
    detalle = admin_client.get(f"{PROYECTOS}{p.pk}/").json()
    assert [j["nombre_completo"] for j in detalle["jurados"]] == ["Ana", "Luis"]  # jurado 1 y jurado 2
    assert detalle["estado_evaluacion"] == "PENDIENTE"


@pytest.mark.parametrize("cuantos", [0, 1, 3])
def test_rn23_se_exigen_exactamente_dos(admin_client, cuantos):
    p = ProyectoFactory()
    r = asignar(admin_client, p, *[JuradoFactory() for _ in range(cuantos)])
    assert r.status_code == 400
    assert "docentes" in r.json()["campos"]
    assert not p.asignaciones.exists()


def test_rn25_los_dos_deben_ser_distintos(admin_client):
    p, d = ProyectoFactory(), JuradoFactory()
    r = asignar(admin_client, p, d, d)
    assert r.status_code == 400
    assert r.json()["campos"]["docentes"] == ["Seleccione dos docentes distintos."]


def test_rn23_no_se_asigna_a_un_proyecto_que_ya_tiene_jurados(admin_client):
    p = ProyectoFactory()
    asignar(admin_client, p, JuradoFactory(), JuradoFactory())
    r = asignar(admin_client, p, JuradoFactory(), JuradoFactory())
    assert r.status_code == 409
    assert r.json()["codigo"] == "PROYECTO_COMPLETO"
    assert p.asignaciones.count() == 2


def test_rn24_maximo_3_proyectos_por_docente_en_el_evento(admin_client, evento):
    ana = JuradoFactory(nombre_completo="Ana")
    for _ in range(3):
        assert asignar(admin_client, ProyectoFactory(evento=evento), ana, JuradoFactory()).status_code == 201
    otro = JuradoFactory()
    p = ProyectoFactory(evento=evento)
    r = asignar(admin_client, p, otro, ana)
    assert r.status_code == 409
    assert r.json() == {
        "detalle": "Ana ya tiene 3 proyectos asignados en este evento.", "codigo": "DOCENTE_SIN_CUPO", "campos": {}
    }
    # Todo o nada: el otro docente tampoco quedó asignado.
    assert not p.asignaciones.exists()
    # En otro evento sí tiene cupo.
    assert asignar(admin_client, ProyectoFactory(evento=EventoFactory()), ana, otro).status_code == 201


def test_no_se_asigna_un_admin_ni_un_docente_inexistente(admin_client):
    from .factories import AdminFactory

    p = ProyectoFactory()
    assert asignar(admin_client, p, AdminFactory(), JuradoFactory()).status_code == 400
    r = admin_client.post(f"{PROYECTOS}{p.pk}/jurados/", {"docentes": [JuradoFactory().pk, 9999]}, format="json")
    assert r.status_code == 400 and "docentes" in r.json()["campos"]
    r = admin_client.post(f"{PROYECTOS}9999/jurados/", {"docentes": [JuradoFactory().pk, JuradoFactory().pk]},
                          format="json")
    assert r.status_code == 404


def test_no_existe_asignacion_de_a_uno(admin_client):
    r = admin_client.post(ASIGNACIONES, {"proyecto": ProyectoFactory().pk, "docente": JuradoFactory().pk}, format="json")
    assert r.status_code == 404


# --- Reemplazar


def test_reemplazar_un_jurado(admin_client):
    p = ProyectoFactory()
    a1, a2 = asignar(admin_client, p, JuradoFactory(nombre_completo="Ana"), JuradoFactory()).json()
    nuevo = JuradoFactory(nombre_completo="Marta")
    r = reemplazar(admin_client, a1["id"], nuevo)
    assert r.status_code == 200
    assert r.json()["docente_nombre"] == "Marta"
    jurados = admin_client.get(f"{PROYECTOS}{p.pk}/").json()["jurados"]
    assert [j["nombre_completo"] for j in jurados][0] == "Marta"  # conserva el puesto de jurado 1
    assert len(jurados) == 2


def test_rn26_no_se_reemplaza_un_jurado_que_ya_evaluo(admin_client):
    e = EvaluacionFactory()
    AsignacionFactory(proyecto=e.asignacion.proyecto)
    r = reemplazar(admin_client, e.asignacion.pk, JuradoFactory())
    assert r.status_code == 409
    assert r.json()["codigo"] == "ASIGNACION_CON_EVALUACION"


def test_se_reemplaza_el_que_no_ha_evaluado(admin_client):
    e = EvaluacionFactory()
    pendiente = AsignacionFactory(proyecto=e.asignacion.proyecto)
    assert reemplazar(admin_client, pendiente.pk, JuradoFactory()).status_code == 200


def test_rn25_reemplazo_por_el_otro_jurado_del_proyecto(admin_client):
    p = ProyectoFactory()
    d1, d2 = JuradoFactory(), JuradoFactory()
    a1, _ = asignar(admin_client, p, d1, d2).json()
    r = reemplazar(admin_client, a1["id"], d2)
    assert r.status_code == 409
    assert r.json()["codigo"] == "ASIGNACION_DUPLICADA"


def test_rn24_reemplazo_respeta_el_cupo(admin_client, evento):
    lleno = JuradoFactory()
    for _ in range(3):
        asignar(admin_client, ProyectoFactory(evento=evento), lleno, JuradoFactory())
    a1, _ = asignar(admin_client, ProyectoFactory(evento=evento), JuradoFactory(), JuradoFactory()).json()
    assert reemplazar(admin_client, a1["id"], lleno).json()["codigo"] == "DOCENTE_SIN_CUPO"


def test_reemplazar_asignacion_inexistente(admin_client):
    assert reemplazar(admin_client, 999, JuradoFactory()).status_code == 404


# --- Quitar


def test_quitar_los_dos_jurados(admin_client):
    p = ProyectoFactory()
    asignar(admin_client, p, JuradoFactory(), JuradoFactory())
    assert admin_client.delete(f"{PROYECTOS}{p.pk}/jurados/").status_code == 204
    assert not Asignacion.objects.exists()
    assert admin_client.get(f"{PROYECTOS}{p.pk}/").json()["estado_evaluacion"] == "SIN_JURADOS"


def test_rn26_no_se_quitan_si_alguno_evaluo(admin_client):
    e = EvaluacionFactory()
    AsignacionFactory(proyecto=e.asignacion.proyecto)
    r = admin_client.delete(f"{PROYECTOS}{e.asignacion.proyecto.pk}/jurados/")
    assert r.status_code == 409
    assert r.json()["codigo"] == "ASIGNACION_CON_EVALUACION"
    assert Asignacion.objects.count() == 2


def test_no_existe_quitar_un_solo_jurado(admin_client):
    a = AsignacionFactory()
    assert admin_client.delete(f"{ASIGNACIONES}{a.pk}/").status_code == 405
    assert Asignacion.objects.filter(pk=a.pk).exists()


def test_cupo_se_libera_al_quitar(admin_client, evento):
    d = JuradoFactory()
    proyectos = [ProyectoFactory(evento=evento) for _ in range(3)]
    for p in proyectos:
        asignar(admin_client, p, d, JuradoFactory())
    admin_client.delete(f"{PROYECTOS}{proyectos[0].pk}/jurados/")
    assert asignar(admin_client, ProyectoFactory(evento=evento), d, JuradoFactory()).status_code == 201
