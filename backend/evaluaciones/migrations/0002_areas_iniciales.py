from django.db import migrations

AREAS = [
    ("IS", "Ingeniería de software"),
    ("IS", "Redes y telemática"),
    ("IS", "Seguridad informática"),
    ("IS", "RV/RA"),
    ("IS", "Ciencia de datos e IA"),
    ("IE", "Control y automatización"),
    ("IC", "Vías, transporte y movilidad"),
    ("IC", "Geotecnia"),
]


def crear_areas(apps, schema_editor):
    AreaConocimiento = apps.get_model("evaluaciones", "AreaConocimiento")
    for programa, nombre in AREAS:
        AreaConocimiento.objects.get_or_create(programa=programa, nombre=nombre)


def borrar_areas(apps, schema_editor):
    AreaConocimiento = apps.get_model("evaluaciones", "AreaConocimiento")
    for programa, nombre in AREAS:
        AreaConocimiento.objects.filter(programa=programa, nombre=nombre).delete()


class Migration(migrations.Migration):
    dependencies = [("evaluaciones", "0001_initial")]
    operations = [migrations.RunPython(crear_areas, borrar_areas)]
