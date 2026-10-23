from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("api/", include("core.urls")),
    path("api/", include("evaluaciones.urls")),
]

if settings.DEBUG:
    from django.contrib import admin

    urlpatterns.append(path("django-admin/", admin.site.urls))

handler404 = "core.excepciones.no_encontrado"
handler500 = "core.excepciones.error_servidor"
