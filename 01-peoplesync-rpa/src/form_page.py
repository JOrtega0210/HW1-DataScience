"""Page Object del formulario PeopleSync (Registro de Nuevo Ingreso).

Selectores verificados directamente contra el DOM real del formulario
(descargado y revisado, no adivinados). El formulario es de una sola
página (ambas secciones visibles a la vez, sin botones "Siguiente"),
100% cliente (sin backend): al registrar, agrega una fila a una tabla
en memoria y limpia el formulario automáticamente.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .data_loader import EmployeeRecord, normalize_text


class ValidationFailedError(Exception):
    """El formulario rechazó los datos (errores de validación visibles)."""

    def __init__(self, messages: list[str]):
        super().__init__("; ".join(messages) or "Errores de validación en el formulario")
        self.messages = messages


@dataclass
class RegistrationResult:
    success: bool
    counter_after: int
    last_row_dni: Optional[str]


class FormPage:
    # --- Selectores (IDs verificados en el HTML real del formulario) ---
    ID_NOMBRES = "nombres"
    ID_DNI = "dni"
    ID_FECHA_NACIMIENTO = "fecha_nacimiento"
    ID_GENERO = "genero"
    ID_TELEFONO = "telefono"
    ID_CORREO = "correo"
    ID_AREA = "area"
    ID_PUESTO = "puesto"
    ID_CONTRATO = "contrato"
    ID_SEDE = "sede"
    ID_FECHA_INGRESO = "fecha_ingreso"
    ID_BTN_REGISTRAR = "btn-registrar"
    ID_COUNTER = "counter"
    ID_TABLA_BODY = "tabla-body"

    RADIO_MODALIDAD_NAME = "modalidad"
    BTN_LIMPIAR_XPATH = "//button[contains(@onclick, 'limpiarFormulario')]"

    def __init__(self, driver: WebDriver, wait_timeout: int, logger: logging.Logger):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)
        self.logger = logger

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _el(self, element_id: str):
        return self.wait.until(EC.presence_of_element_located((By.ID, element_id)))

    def _set_text(self, element_id: str, value: str) -> None:
        el = self._el(element_id)
        el.clear()
        el.send_keys(value)

    def _set_date(self, element_id: str, value_yyyy_mm_dd: str) -> None:
        """Setea un input[type=date] vía JS (evita problemas de locale con send_keys)."""
        el = self._el(element_id)
        self.driver.execute_script(
            """
            const el = arguments[0];
            const value = arguments[1];
            el.value = value;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            el,
            value_yyyy_mm_dd,
        )

    def _select_by_text_normalized(self, element_id: str, visible_text: str) -> None:
        el = self._el(element_id)
        select = Select(el)
        try:
            select.select_by_visible_text(visible_text)
            return
        except NoSuchElementException:
            pass

        target = normalize_text(visible_text)
        for option in select.options:
            if normalize_text(option.text) == target:
                select.select_by_visible_text(option.text)
                return

        available = [o.text for o in select.options]
        raise NoSuchElementException(
            f"No se encontró la opción '{visible_text}' en #{element_id}. "
            f"Opciones disponibles: {available}"
        )

    def _click(self, element) -> None:
        """Click robusto: centra el elemento en el viewport (evita quedar tapado
        por la topbar sticky o el status-bar fijo) y cae a un click por JS si
        el click nativo es interceptado por otro elemento superpuesto.
        """
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
            element,
        )
        try:
            element.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", element)

    def _click_modalidad(self, value: str) -> None:
        xpath = (
            f"//input[@name='{self.RADIO_MODALIDAD_NAME}' and @value='{value}']/parent::label"
        )
        label = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        self._click(label)

    # ------------------------------------------------------------------
    # Llenado de formulario
    # ------------------------------------------------------------------

    def fill_employee(self, record: EmployeeRecord) -> None:
        self._set_text(self.ID_NOMBRES, record.nombres)
        self._set_text(self.ID_DNI, record.dni)
        self._set_date(self.ID_FECHA_NACIMIENTO, record.fecha_nacimiento)
        self._select_by_text_normalized(self.ID_GENERO, record.genero_valor_formulario)
        self._set_text(self.ID_TELEFONO, record.telefono)
        self._set_text(self.ID_CORREO, record.correo)

        self._select_by_text_normalized(self.ID_AREA, record.area)
        self._select_by_text_normalized(self.ID_PUESTO, record.puesto)
        self._select_by_text_normalized(self.ID_CONTRATO, record.contrato)
        self._select_by_text_normalized(self.ID_SEDE, record.sede)
        self._set_date(self.ID_FECHA_INGRESO, record.fecha_ingreso)
        self._click_modalidad(record.modalidad)

    # ------------------------------------------------------------------
    # Envío y verificación
    # ------------------------------------------------------------------

    def get_counter(self) -> int:
        text = self._el(self.ID_COUNTER).text.strip()
        return int(text) if text.isdigit() else 0

    def _get_field_errors(self) -> list[str]:
        elements = self.driver.find_elements(By.CSS_SELECTOR, ".field-error.show")
        return [e.text.strip() for e in elements if e.text.strip()]

    def _last_row_dni(self) -> Optional[str]:
        rows = self.driver.find_elements(By.CSS_SELECTOR, f"#{self.ID_TABLA_BODY} tr")
        if not rows:
            return None
        cells = rows[-1].find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            return None
        return cells[1].text.strip()

    def submit_and_verify(self, expected_dni: str, previous_counter: int) -> RegistrationResult:
        """Hace click en 'Registrar Ingreso' y confirma el alta de forma robusta.

        Espera hasta que el contador incremente Y la última fila de la
        tabla tenga el DNI esperado. Si en cambio aparecen errores de
        validación visibles, levanta ValidationFailedError.
        """
        btn = self.wait.until(EC.element_to_be_clickable((By.ID, self.ID_BTN_REGISTRAR)))
        self._click(btn)

        expected_counter = previous_counter + 1

        try:
            self.wait.until(
                lambda d: self.get_counter() == expected_counter
                and self._last_row_dni() == expected_dni
            )
        except TimeoutException:
            errors = self._get_field_errors()
            if errors:
                raise ValidationFailedError(errors)
            raise TimeoutException(
                f"No se pudo confirmar el alta de DNI={expected_dni}: "
                f"contador esperado={expected_counter}, actual={self.get_counter()}, "
                f"última fila DNI={self._last_row_dni()}"
            )

        return RegistrationResult(
            success=True,
            counter_after=self.get_counter(),
            last_row_dni=self._last_row_dni(),
        )

    def reset_form(self) -> None:
        """Limpia manualmente el formulario (por si quedó con datos tras un error)."""
        try:
            btn = self.driver.find_element(By.XPATH, self.BTN_LIMPIAR_XPATH)
            self._click(btn)
        except NoSuchElementException:
            self.logger.warning("No se encontró el botón 'Limpiar'; se continúa de todos modos.")
