"""Orquestador del bot RPA de registro de empleados en PeopleSync.

Flujo:
    1. Carga configuración (.env + argparse).
    2. Configura logging (consola + archivo en logs/).
    3. Lee y normaliza el Excel de empleados.
    4. Abre el navegador una sola vez y navega al formulario.
    5. Por cada empleado: llena el formulario, registra, verifica el alta
       (contador + fila en la tabla) y continúa con el siguiente SIN
       recargar la página (el propio formulario se limpia solo al
       registrar exitosamente).
    6. Un error en un registro no detiene el lote: se loguea, se toma
       captura de pantalla, se limpia el formulario y se continúa.
    7. Al final, imprime/loguea el resumen (exitosos, omitidos, fallidos).
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from selenium.common.exceptions import WebDriverException

from .config import load_config
from .data_loader import load_employees
from .driver_factory import build_chrome_driver
from .form_page import FormPage, ValidationFailedError
from .logger_setup import setup_logger
from .report_writer import write_report
from .state_store import StateStore


def _take_screenshot(driver, screenshot_dir: str, dni: str, logger) -> None:
    try:
        path = Path(screenshot_dir)
        path.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = path / f"error_{dni}_{timestamp}.png"
        driver.save_screenshot(str(filename))
        logger.error("Captura de pantalla guardada en: %s", filename)
    except WebDriverException as exc:
        logger.error("No se pudo guardar la captura de pantalla: %s", exc)


def run(argv: list[str] | None = None) -> int:
    config = load_config(argv)
    logger = setup_logger(config.log_dir, config.log_level)

    logger.info("=== Bot RPA PeopleSync - Registro de Ingresos ===")
    logger.info("Formulario: %s", config.form_url)
    logger.info("Excel: %s", config.excel_path)
    logger.info("Headless: %s | Resume: %s | Límite: %s", config.headless, config.resume, config.max_records)

    records = load_employees(
        excel_path=config.excel_path,
        genero_unsupported_action=config.genero_unsupported_action,
        genero_default_value=config.genero_default_value,
        sheet_name=config.excel_sheet_name,
    )
    logger.info("Registros leídos del Excel: %d", len(records))

    if config.max_records is not None:
        records = records[: config.max_records]
        logger.info("Aplicando límite de prueba: se procesarán %d registros", len(records))

    state_store = StateStore(config.state_file)

    exitosos: list[str] = []
    omitidos_genero: list[tuple[str, str]] = []
    omitidos_resume: list[str] = []
    fallidos: list[tuple[str, str]] = []
    resultados: list[dict] = []

    driver = build_chrome_driver(
        headless=config.headless,
        implicit_wait_seconds=config.implicit_wait_seconds,
        chromedriver_path=config.chromedriver_path,
        logger=logger,
    )

    try:
        driver.get(config.form_url)
        form = FormPage(driver, config.explicit_wait_seconds, logger)

        for i, record in enumerate(records, start=1):
            prefix = f"[{i}/{len(records)}] DNI={record.dni} - {record.nombres}"

            if not record.genero_soportado:
                reason = "; ".join(record.warnings) or "Género no soportado por el formulario"
                logger.warning("%s -> OMITIDO (género no soportado): %s", prefix, reason)
                omitidos_genero.append((record.dni, reason))
                resultados.append(
                    {"dni": record.dni, "nombres": record.nombres, "estado": "No cargado", "motivo": reason}
                )
                continue

            if config.resume and state_store.is_registered(record.dni):
                logger.info("%s -> OMITIDO (ya registrado en una corrida previa, modo resume)", prefix)
                omitidos_resume.append(record.dni)
                resultados.append(
                    {
                        "dni": record.dni,
                        "nombres": record.nombres,
                        "estado": "Omitido (resume)",
                        "motivo": "Ya registrado en una corrida previa",
                    }
                )
                continue

            for warning in record.warnings:
                logger.warning("%s -> Advertencia: %s", prefix, warning)

            try:
                previous_counter = form.get_counter()
                form.fill_employee(record)
                result = form.submit_and_verify(record.dni, previous_counter)

                logger.info(
                    "%s -> REGISTRADO OK (contador=%d, fila confirmada DNI=%s)",
                    prefix,
                    result.counter_after,
                    result.last_row_dni,
                )
                exitosos.append(record.dni)
                state_store.mark_registered(record.dni)
                resultados.append(
                    {"dni": record.dni, "nombres": record.nombres, "estado": "Cargado", "motivo": ""}
                )

            except ValidationFailedError as exc:
                reason = f"Validación: {'; '.join(exc.messages)}"
                logger.error("%s -> FALLÓ validación del formulario: %s", prefix, exc.messages)
                _take_screenshot(driver, config.screenshot_dir, record.dni, logger)
                fallidos.append((record.dni, reason))
                resultados.append(
                    {"dni": record.dni, "nombres": record.nombres, "estado": "No cargado", "motivo": reason}
                )
                form.reset_form()

            except Exception as exc:  # noqa: BLE001 - un fallo no debe detener el lote
                logger.error("%s -> ERROR inesperado: %s", prefix, exc)
                logger.debug(traceback.format_exc())
                _take_screenshot(driver, config.screenshot_dir, record.dni, logger)
                fallidos.append((record.dni, str(exc)))
                resultados.append(
                    {"dni": record.dni, "nombres": record.nombres, "estado": "No cargado", "motivo": str(exc)}
                )
                try:
                    form.reset_form()
                except Exception:  # noqa: BLE001 - último recurso, no debe romper el loop
                    logger.error("No se pudo limpiar el formulario tras el error; se intentará continuar.")

    finally:
        if config.headless:
            driver.quit()
        else:
            logger.info("Navegador dejado abierto (modo no headless). Ciérralo manualmente cuando termines.")

    total = len(records)
    no_cargados = omitidos_genero + fallidos  # datos inválidos/no soportados + errores técnicos

    logger.info("=" * 60)
    logger.info("RESUMEN FINAL")
    logger.info("Total de registros procesados: %d", total)
    logger.info("Registros cargados exitosamente: %d", len(exitosos))
    logger.info("Registros que NO se pudieron cargar: %d", len(no_cargados))
    for dni, reason in no_cargados:
        logger.info("  - DNI %s: %s", dni, reason)
    if omitidos_resume:
        logger.info(
            "Omitidos por modo resume (ya registrados en una corrida previa, no reintentados): %d",
            len(omitidos_resume),
        )
    logger.info("=" * 60)

    write_report(
        resultados=resultados,
        total=total,
        exitosos=len(exitosos),
        no_cargados=len(no_cargados),
        omitidos_resume=len(omitidos_resume),
        report_dir=config.report_dir,
        logger=logger,
    )

    return 0 if not fallidos else 1


if __name__ == "__main__":
    sys.exit(run())
