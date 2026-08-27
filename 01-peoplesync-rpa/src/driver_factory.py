"""Construcción del WebDriver de Chrome.

Orden de resolución del driver (para poder correr fuera del entorno de
desarrollo sin depender de una versión de chromedriver fijada a mano):
    1. Si se configura CHROMEDRIVER_PATH -> se usa esa ruta directamente.
    2. Si no, se usa el Selenium Manager incorporado en Selenium >= 4.6,
       que descarga y resuelve automáticamente la versión de chromedriver
       compatible con el Chrome instalado en la máquina.

No se usa el paquete `webdriver-manager`: quedó desactualizado frente a
versiones recientes de Chrome (151+) y puede devolver silenciosamente un
chromedriver incompatible sin lanzar ninguna excepción.
"""

from __future__ import annotations

import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def build_chrome_driver(
    headless: bool,
    implicit_wait_seconds: int,
    chromedriver_path: Optional[str],
    logger: logging.Logger,
) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service: Optional[Service] = None

    if chromedriver_path:
        logger.info("Usando chromedriver configurado manualmente: %s", chromedriver_path)
        service = Service(executable_path=chromedriver_path)
    else:
        # webdriver-manager (4.0.2) no reconoce versiones de Chrome recientes
        # (151+) y puede devolver silenciosamente un chromedriver desactualizado
        # sin lanzar excepción. El Selenium Manager incorporado en Selenium >= 4.6
        # resuelve la versión correcta de forma confiable, así que se usa
        # directamente en lugar de webdriver-manager.
        logger.info("Usando el Selenium Manager incorporado para resolver chromedriver.")
        service = None

    driver = webdriver.Chrome(service=service, options=options) if service else webdriver.Chrome(options=options)
    driver.implicitly_wait(implicit_wait_seconds)
    return driver
