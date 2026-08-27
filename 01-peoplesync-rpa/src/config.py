"""Carga de configuración desde .env y argumentos de línea de comandos.

Prioridad de resolución de cada valor: argumentos CLI > variables de
entorno (.env) > valores por defecto definidos aquí.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os


def _str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    return int(value)


@dataclass
class Config:
    form_url: str
    excel_path: str
    excel_sheet_name: Optional[str]
    headless: bool
    explicit_wait_seconds: int
    implicit_wait_seconds: int
    chromedriver_path: Optional[str]
    log_dir: str
    screenshot_dir: str
    report_dir: str
    log_level: str
    state_file: str
    resume: bool
    max_records: Optional[int]
    genero_unsupported_action: str
    genero_default_value: str


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bot RPA para registrar empleados en el formulario PeopleSync HRIS."
    )
    parser.add_argument("--env-file", default=".env", help="Ruta al archivo .env a cargar (default: .env)")
    parser.add_argument("--url", dest="form_url", default=None, help="URL del formulario web")
    parser.add_argument("--excel", dest="excel_path", default=None, help="Ruta al archivo Excel con el dataset")
    parser.add_argument("--sheet", dest="excel_sheet_name", default=None, help="Nombre de la hoja del Excel a leer")
    parser.add_argument("--headless", dest="headless", action="store_true", default=None, help="Ejecutar Chrome en modo headless")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Ejecutar Chrome con ventana visible")
    parser.add_argument("--chromedriver-path", dest="chromedriver_path", default=None, help="Ruta local a chromedriver.exe (solo si no hay internet para el Selenium Manager)")
    parser.add_argument("--log-dir", dest="log_dir", default=None, help="Carpeta para archivos de log")
    parser.add_argument("--screenshot-dir", dest="screenshot_dir", default=None, help="Carpeta para capturas de error")
    parser.add_argument("--report-dir", dest="report_dir", default=None, help="Carpeta para el reporte .xlsx de resultados")
    parser.add_argument("--log-level", dest="log_level", default=None, help="Nivel de logging (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--state-file", dest="state_file", default=None, help="Ruta al archivo de estado usado por --resume")
    parser.add_argument("--resume", dest="resume", action="store_true", default=None, help="Omitir DNIs ya registrados en corridas previas")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Ignorar el estado previo y procesar todos los registros")
    parser.add_argument("--limit", dest="max_records", type=int, default=None, help="Procesar solo los primeros N registros del Excel (útil para pruebas)")
    parser.add_argument("--explicit-wait", dest="explicit_wait_seconds", type=int, default=None, help="Timeout en segundos para WebDriverWait")
    parser.add_argument("--implicit-wait", dest="implicit_wait_seconds", type=int, default=None, help="Timeout en segundos para espera implícita del driver")
    parser.add_argument(
        "--genero-unsupported-action",
        dest="genero_unsupported_action",
        default=None,
        choices=["skip", "default", "alternate"],
        help="Qué hacer con valores de género no soportados por el formulario",
    )
    return parser


def load_config(argv: Optional[list[str]] = None) -> Config:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    env_path = Path(args.env_file)
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        # Permite ejecutar sin .env si todo se pasa por CLI o variables de entorno del sistema
        load_dotenv(override=False)

    def env(name: str, default: str = "") -> str:
        return os.getenv(name, default)

    form_url = args.form_url or env("FORM_URL")
    excel_path = args.excel_path or env("EXCEL_PATH")
    excel_sheet_name = args.excel_sheet_name if args.excel_sheet_name is not None else (env("EXCEL_SHEET_NAME") or None)

    headless = args.headless if args.headless is not None else _str_to_bool(env("HEADLESS", "false"))
    explicit_wait_seconds = args.explicit_wait_seconds if args.explicit_wait_seconds is not None else int(env("EXPLICIT_WAIT_SECONDS", "15"))
    implicit_wait_seconds = args.implicit_wait_seconds if args.implicit_wait_seconds is not None else int(env("IMPLICIT_WAIT_SECONDS", "2"))
    chromedriver_path = args.chromedriver_path or (env("CHROMEDRIVER_PATH") or None)
    log_dir = args.log_dir or env("LOG_DIR", "./logs")
    screenshot_dir = args.screenshot_dir or env("SCREENSHOT_DIR", "./screenshots")
    report_dir = args.report_dir or env("REPORT_DIR", "./reports")
    log_level = (args.log_level or env("LOG_LEVEL", "INFO")).upper()
    state_file = args.state_file or env("STATE_FILE", "./state/registrados.json")
    resume = args.resume if args.resume is not None else _str_to_bool(env("RESUME", "false"))
    max_records = args.max_records if args.max_records is not None else _optional_int(env("MAX_RECORDS", ""))
    genero_unsupported_action = args.genero_unsupported_action or env("GENERO_UNSUPPORTED_ACTION", "skip")
    genero_default_value = env("GENERO_DEFAULT_VALUE", "Masculino")

    if not form_url:
        raise ValueError("FORM_URL no está configurado (usa .env o --url)")
    if not excel_path:
        raise ValueError("EXCEL_PATH no está configurado (usa .env o --excel)")

    return Config(
        form_url=form_url,
        excel_path=excel_path,
        excel_sheet_name=excel_sheet_name,
        headless=headless,
        explicit_wait_seconds=explicit_wait_seconds,
        implicit_wait_seconds=implicit_wait_seconds,
        chromedriver_path=chromedriver_path,
        log_dir=log_dir,
        screenshot_dir=screenshot_dir,
        report_dir=report_dir,
        log_level=log_level,
        state_file=state_file,
        resume=resume,
        max_records=max_records,
        genero_unsupported_action=genero_unsupported_action,
        genero_default_value=genero_default_value,
    )
