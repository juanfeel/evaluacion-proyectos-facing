from django.urls import path

from . import views

urlpatterns = [
    path("admin/eventos/", views.EventosView.as_view(), name="admin-eventos"),
    path("admin/eventos/<int:pk>/", views.EventoDetalleView.as_view(), name="admin-evento"),
    path("admin/eventos/<int:pk>/activar/", views.ActivarEventoView.as_view(), name="admin-evento-activar"),
    path("admin/areas/", views.AreasView.as_view(), name="admin-areas"),
    path("admin/proyectos/", views.ProyectosView.as_view(), name="admin-proyectos"),
    path("admin/proyectos/<int:pk>/", views.ProyectoDetalleView.as_view(), name="admin-proyecto"),
    path(
        "admin/proyectos/<int:pk>/evaluaciones/",
        views.EvaluacionesProyectoView.as_view(),
        name="admin-proyecto-evaluaciones",
    ),
    path("admin/resultados/", views.ResultadosView.as_view(), name="admin-resultados"),
    path("admin/resumen/", views.ResumenView.as_view(), name="admin-resumen"),
    path("admin/proyectos/<int:pk>/jurados/", views.JuradosProyectoView.as_view(), name="admin-proyecto-jurados"),
    path("admin/asignaciones/<int:pk>/", views.AsignacionDetalleView.as_view(), name="admin-asignacion"),
    path("jurado/asignaciones/", views.MisAsignacionesView.as_view(), name="jurado-asignaciones"),
    path("jurado/asignaciones/<int:pk>/formulario/", views.FormularioView.as_view(), name="jurado-formulario"),
    path("jurado/asignaciones/<int:pk>/evaluacion/", views.EvaluacionView.as_view(), name="jurado-evaluacion"),
]
