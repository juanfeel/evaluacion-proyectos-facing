from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/refresh/", views.RefreshView.as_view(), name="refresh"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("auth/cambiar-password/", views.CambiarPasswordView.as_view(), name="cambiar-password"),
]

urlpatterns += [
    path("admin/docentes/", views.DocentesView.as_view(), name="admin-docentes"),
    path("admin/docentes/<int:pk>/", views.DocenteDetalleView.as_view(), name="admin-docente"),
    path(
        "admin/docentes/<int:pk>/restablecer-password/",
        views.RestablecerPasswordView.as_view(),
        name="admin-docente-restablecer",
    ),
]
