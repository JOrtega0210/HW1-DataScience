"""
Scraper del Tipo de Cambio Oficial (SUNAT).
Fuente: https://e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias

Recorre el calendario mensual publicado por SUNAT desde un mes/año de inicio
hasta un mes/año final (por defecto: enero 2024 -> mes actual), extrae la
fecha, el tipo de cambio de compra y el de venta de cada dia, y consolida
todo en un unico archivo CSV.
"""
import argparse
import logging
import os
import sys
import time
from datetime import date, datetime

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL = "https://e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias"
WAIT_TIMEOUT = 20

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def setup_logging():
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, f"scraper_{datetime.now():%Y%m%d_%H%M%S}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


def parse_periodo(valor):
    try:
        anio, mes = valor.split("-")
        anio, mes = int(anio), int(mes)
        if not 1 <= mes <= 12:
            raise ValueError
        return anio, mes
    except ValueError:
        raise SystemExit(f"Formato de periodo invalido: '{valor}'. Use YYYY-MM (ej: 2024-01)")


def parse_args():
    hoy = date.today()
    parser = argparse.ArgumentParser(description="Scraper del tipo de cambio oficial SUNAT")
    parser.add_argument("--desde", default="2024-01", help="Mes/anio de inicio, formato YYYY-MM (default: 2024-01)")
    parser.add_argument("--hasta", default=hoy.strftime("%Y-%m"), help="Mes/anio final, formato YYYY-MM (default: mes actual)")
    parser.add_argument("--salida", default=os.path.join(BASE_DIR, "output", "tipo_cambio_sunat.csv"), help="Ruta del CSV de salida")
    parser.add_argument("--espera", type=float, default=1.5, help="Segundos de espera entre cada navegacion de mes (default: 1.5)")
    parser.add_argument("--con-ventana", dest="headless", action="store_false", default=True, help="Muestra la ventana de Chrome (por defecto corre en headless)")
    return parser.parse_args()


def mes_index(anio, mes):
    return anio * 12 + mes


def crear_driver(headless):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        # El WAF de SUNAT rechaza la peticion (ERR_EMPTY_RESPONSE) si el
        # User-Agent incluye "HeadlessChrome", que es lo que Chrome envia
        # por defecto en modo headless. Se fuerza un User-Agent de
        # escritorio normal para que la pagina cargue igual que en una
        # ventana visible.
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        )
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def leer_mes_anio(driver):
    # El calendario re-renderiza estos botones en cada navegacion, por lo
    # que una referencia obtenida a mitad de ese repintado puede quedar
    # "stale" entre la lectura del mes y la del anio; se reintenta en
    # lugar de dejar que la excepcion tumbe todo el scraping.
    for _ in range(5):
        try:
            mes = driver.find_element(By.CSS_SELECTOR, "button.js-cal-option.disabled").text.strip()
            anio = driver.find_element(By.CSS_SELECTOR, "button.js-cal-years.disabled").text.strip()
            return mes, int(anio)
        except StaleElementReferenceException:
            time.sleep(0.2)
    raise TimeoutException("No se pudo leer el mes/anio del calendario (elementos inestables)")


def esperar_calendario_listo(driver, estado_previo):
    WebDriverWait(driver, WAIT_TIMEOUT, ignored_exceptions=(StaleElementReferenceException,)).until(
        lambda d: leer_mes_anio(d) != estado_previo
    )
    WebDriverWait(driver, WAIT_TIMEOUT, ignored_exceptions=(StaleElementReferenceException,)).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "td.calendar-day.current .event"))
    )


def navegar(driver, direccion, espera):
    selector = "button.js-cal-prev" if direccion == "prev" else "button.js-cal-next"
    estado_previo = leer_mes_anio(driver)
    boton = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    boton.click()
    esperar_calendario_listo(driver, estado_previo)
    time.sleep(espera)


def extraer_mes(driver, anio, mes):
    filas = []
    celdas = driver.find_elements(By.CSS_SELECTOR, "td.calendar-day.current")
    for celda in celdas:
        try:
            dia = int(celda.find_element(By.CSS_SELECTOR, ".date").text.strip())
        except (NoSuchElementException, ValueError):
            continue

        compra = venta = None
        for evento in celda.find_elements(By.CSS_SELECTOR, ".event"):
            texto = evento.text.strip()
            partes = texto.split()
            if not partes:
                continue
            etiqueta, valor = partes[0].lower(), partes[-1]
            if etiqueta.startswith("compra"):
                compra = valor
            elif etiqueta.startswith("venta"):
                venta = valor

        try:
            fecha = date(anio, mes, dia)
        except ValueError:
            logging.warning("Dia invalido descartado: %04d-%02d-%02d", anio, mes, dia)
            continue

        estado = "OK" if compra and venta else "SIN_DATO_PUBLICADO"
        if estado != "OK":
            logging.warning("Sin tipo de cambio publicado para %s", fecha.isoformat())

        filas.append({"fecha": fecha.isoformat(), "compra": compra, "venta": venta, "estado": estado})
    return filas


def main():
    args = parse_args()
    log_file = setup_logging()
    logging.info("Inicio de ejecucion. Log: %s", log_file)

    anio_desde, mes_desde = parse_periodo(args.desde)
    anio_hasta, mes_hasta = parse_periodo(args.hasta)
    if mes_index(anio_desde, mes_desde) > mes_index(anio_hasta, mes_hasta):
        raise SystemExit("El periodo '--desde' no puede ser posterior a '--hasta'")

    os.makedirs(os.path.dirname(args.salida), exist_ok=True)

    driver = crear_driver(args.headless)
    resultados = []
    try:
        logging.info("Abriendo %s", URL)
        driver.get(URL)
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.js-cal-option.disabled"))
        )
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "td.calendar-day.current .event"))
        )

        mes_actual_txt, anio_actual = leer_mes_anio(driver)
        mes_actual_num = MESES[mes_actual_txt.lower()]

        pasos_atras = mes_index(anio_actual, mes_actual_num) - mes_index(anio_desde, mes_desde)
        if pasos_atras < 0:
            raise SystemExit("El periodo '--desde' esta en el futuro respecto al mes actual del portal SUNAT")

        logging.info("Retrocediendo %d mes(es) hasta %04d-%02d", pasos_atras, anio_desde, mes_desde)
        for _ in range(pasos_atras):
            navegar(driver, "prev", args.espera)

        total_meses = mes_index(anio_hasta, mes_hasta) - mes_index(anio_desde, mes_desde) + 1
        anio_cursor, mes_cursor = anio_desde, mes_desde
        for i in range(total_meses):
            mes_txt, anio_txt = leer_mes_anio(driver)
            logging.info("Extrayendo %s %s (%d/%d)", mes_txt, anio_txt, i + 1, total_meses)
            try:
                filas = extraer_mes(driver, anio_cursor, mes_cursor)
            except Exception:
                logging.exception("Fallo al extraer %04d-%02d, se omite este mes", anio_cursor, mes_cursor)
                filas = []
            logging.info("  %d dia(s) extraido(s)", len(filas))
            resultados.extend(filas)

            if i < total_meses - 1:
                navegar(driver, "next", args.espera)
                mes_cursor += 1
                if mes_cursor > 12:
                    mes_cursor = 1
                    anio_cursor += 1
    finally:
        driver.quit()

    if not resultados:
        logging.warning("No se extrajo ningun dato, no se genera CSV")
        return

    df = pd.DataFrame(resultados).drop_duplicates(subset="fecha").sort_values("fecha")
    df.to_csv(args.salida, index=False, encoding="utf-8-sig")
    logging.info("Guardado %d fila(s) en %s", len(df), args.salida)

    sin_dato = int((df["estado"] != "OK").sum())
    if sin_dato:
        logging.info("%d dia(s) sin tipo de cambio publicado (ver detalle en el log)", sin_dato)

    logging.info("Ejecucion finalizada correctamente")


if __name__ == "__main__":
    main()
