"""Alinea la rúbrica con los anexos 6 (Investigación) y 7 (DTI) actualizados.

Cambian los rótulos EN_CURSO de los criterios 3 y 4 de DTI. Solo se actualizan Criterio y
DescriptorCriterio; las evaluaciones ya enviadas conservan su copia de nombre_criterio (RN-39).
"""

from django.db import migrations

from evaluaciones.rubricas import sincronizar_rubricas


def actualizar(apps, schema_editor):
    sincronizar_rubricas(
        apps.get_model("evaluaciones", "Criterio"),
        apps.get_model("evaluaciones", "DescriptorCriterio"),
    )


class Migration(migrations.Migration):
    dependencies = [("evaluaciones", "0003_rubricas")]
    operations = [migrations.RunPython(actualizar, migrations.RunPython.noop)]
