from django.db import migrations

from evaluaciones.rubricas import sincronizar_rubricas


def cargar(apps, schema_editor):
    sincronizar_rubricas(
        apps.get_model("evaluaciones", "Criterio"),
        apps.get_model("evaluaciones", "DescriptorCriterio"),
    )


def borrar(apps, schema_editor):
    apps.get_model("evaluaciones", "Criterio").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("evaluaciones", "0002_areas_iniciales")]
    operations = [migrations.RunPython(cargar, borrar)]
