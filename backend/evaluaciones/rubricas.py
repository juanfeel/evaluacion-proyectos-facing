"""Lectura de `data/rubricas.yaml`, la fuente de verdad de las rúbricas (CLAUDE.md, sección 6)."""

from functools import lru_cache
from pathlib import Path

import yaml

RUTA_RUBRICAS = Path(__file__).resolve().parent / "data" / "rubricas.yaml"
TIPOS = ("INV", "DTI")
ESTADOS_DESCRIPTOR = ("BASE", "PROPUESTA", "EN_CURSO")


@lru_cache(maxsize=1)
def cargar_rubricas() -> dict:
    """Contenido del YAML. Es un archivo de solo lectura: se puede cachear por proceso."""
    with RUTA_RUBRICAS.open(encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def sincronizar_rubricas(Criterio, DescriptorCriterio) -> None:
    """Crea o actualiza criterios y descriptores según el YAML.

    Recibe los modelos como parámetros para poder usarse con los modelos históricos
    de una migración de datos. Es idempotente.
    """
    datos = cargar_rubricas()
    for tipo in TIPOS:
        for item in datos[tipo]:
            criterio, _ = Criterio.objects.update_or_create(
                tipo=tipo, orden=item["orden"], defaults={"puntajes": item["puntajes"]}
            )
            for estado in ESTADOS_DESCRIPTOR:
                if estado in item:
                    DescriptorCriterio.objects.update_or_create(
                        criterio=criterio,
                        estado=estado,
                        defaults={
                            "nombre": item[estado]["nombre"],
                            "descriptores": item[estado]["descriptores"],
                        },
                    )
                else:
                    DescriptorCriterio.objects.filter(criterio=criterio, estado=estado).delete()
