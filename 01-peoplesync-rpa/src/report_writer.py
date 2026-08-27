"""Exportación del reporte de resultados de una corrida a Excel.

Mejora de innovación sobre el mínimo pedido: además del log de texto,
cada corrida genera un archivo `.xlsx` en `REPORT_DIR` con el detalle
fila por fila (DNI, nombre, estado, motivo) y una hoja de resumen con los
totales — listo para adjuntar como evidencia o revisar en Excel sin tener
que parsear el log.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd


def write_report(
    resultados: list[dict],
    total: int,
    exitosos: int,
    no_cargados: int,
    omitidos_resume: int,
    report_dir: str,
    logger: logging.Logger,
) -> Path:
    path = Path(report_dir)
    path.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = path / f"reporte_{timestamp}.xlsx"

    detalle_df = pd.DataFrame(
        resultados,
        columns=["dni", "nombres", "estado", "motivo"],
    )
    resumen_df = pd.DataFrame(
        [
            {"métrica": "Total de registros procesados", "valor": total},
            {"métrica": "Registros cargados exitosamente", "valor": exitosos},
            {"métrica": "Registros que NO se pudieron cargar", "valor": no_cargados},
            {"métrica": "Omitidos por modo resume", "valor": omitidos_resume},
        ]
    )

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        resumen_df.to_excel(writer, sheet_name="Resumen", index=False)
        detalle_df.to_excel(writer, sheet_name="Detalle", index=False)

    logger.info("Reporte de resultados exportado a: %s", filename)
    return filename
