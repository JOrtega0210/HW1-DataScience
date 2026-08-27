"""Lectura y normalización del dataset de empleados desde Excel.

Columnas esperadas en el Excel (verificadas contra el archivo real
Ingreso_Personal_Agosto.xlsx):
    apellidos_nombres, dni, fecha_nacimiento, genero, telefono, correo,
    area, puesto, contrato, sede, fecha_ingreso, modalidad

Mapeo columna -> campo del formulario PeopleSync:
    apellidos_nombres -> #nombres
    dni               -> #dni
    fecha_nacimiento  -> #fecha_nacimiento (AAAA-MM-DD)
    genero            -> #genero (select: solo "Masculino"/"Femenino")
    telefono          -> #telefono
    correo            -> #correo
    area              -> #area (select)
    puesto            -> #puesto (select con optgroups)
    contrato          -> #contrato (select)
    sede              -> #sede (select con optgroups)
    fecha_ingreso     -> #fecha_ingreso (AAAA-MM-DD)
    modalidad         -> input[name=modalidad] (radio-pill)
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# El <select id="genero"> del formulario solo ofrece estas dos opciones.
GENERO_OPCIONES_SOPORTADAS = {"Masculino", "Femenino"}

REQUIRED_COLUMNS = [
    "apellidos_nombres",
    "dni",
    "fecha_nacimiento",
    "genero",
    "telefono",
    "correo",
    "area",
    "puesto",
    "contrato",
    "sede",
    "fecha_ingreso",
    "modalidad",
]


def normalize_text(value: str) -> str:
    """Normaliza texto para comparaciones tolerantes a espacios/acentos/mayúsculas."""
    if value is None:
        return ""
    text = str(value).strip()
    text = " ".join(text.split())  # colapsa espacios múltiples
    text = unicodedata.normalize("NFKD", text)
    return text.casefold()


@dataclass
class EmployeeRecord:
    row_index: int
    nombres: str
    dni: str
    fecha_nacimiento: str
    genero_original: str
    genero_valor_formulario: Optional[str]
    genero_soportado: bool
    telefono: str
    correo: str
    area: str
    puesto: str
    contrato: str
    sede: str
    fecha_ingreso: str
    modalidad: str
    warnings: list[str] = field(default_factory=list)


def _resolve_genero(
    genero_original: str,
    row_position: int,
    action: str,
    default_value: str,
) -> tuple[Optional[str], bool, Optional[str]]:
    """Determina el valor de género a usar en el formulario.

    Retorna (valor_para_formulario, soportado, warning).
    Si `soportado` es False, el registro debe omitirse (acción "skip").
    """
    genero_stripped = str(genero_original).strip()
    if genero_stripped in GENERO_OPCIONES_SOPORTADAS:
        return genero_stripped, True, None

    warning = (
        f"Valor de género '{genero_original}' no está entre las opciones del "
        f"formulario ({', '.join(sorted(GENERO_OPCIONES_SOPORTADAS))})."
    )

    if action == "skip":
        return None, False, warning
    if action == "default":
        return default_value, True, warning + f" Se forzó a '{default_value}'."
    if action == "alternate":
        alternado = "Masculino" if row_position % 2 == 0 else "Femenino"
        return alternado, True, warning + f" Se alternó a '{alternado}'."

    raise ValueError(f"GENERO_UNSUPPORTED_ACTION desconocido: {action}")


def load_employees(
    excel_path: str,
    genero_unsupported_action: str = "skip",
    genero_default_value: str = "Masculino",
    sheet_name: Optional[str] = None,
) -> list[EmployeeRecord]:
    """Lee el Excel y devuelve una lista de EmployeeRecord normalizados."""

    df = pd.read_excel(excel_path, sheet_name=sheet_name if sheet_name else 0)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas obligatorias en el Excel: {missing}. "
            f"Columnas encontradas: {list(df.columns)}"
        )

    records: list[EmployeeRecord] = []
    genero_unsupported_action = (genero_unsupported_action or "skip").strip().lower()

    for position, (idx, row) in enumerate(df.iterrows()):
        warnings: list[str] = []

        dni = str(row["dni"]).strip()
        if dni.endswith(".0"):
            dni = dni[:-2]
        dni = dni.zfill(8)

        telefono = str(row["telefono"]).strip()
        if telefono.endswith(".0"):
            telefono = telefono[:-2]

        fecha_nacimiento = pd.Timestamp(row["fecha_nacimiento"]).strftime("%Y-%m-%d")
        fecha_ingreso = pd.Timestamp(row["fecha_ingreso"]).strftime("%Y-%m-%d")

        genero_valor, genero_soportado, genero_warning = _resolve_genero(
            genero_original=row["genero"],
            row_position=position,
            action=genero_unsupported_action,
            default_value=genero_default_value,
        )
        if genero_warning:
            warnings.append(genero_warning)

        record = EmployeeRecord(
            row_index=idx,
            nombres=str(row["apellidos_nombres"]).strip(),
            dni=dni,
            fecha_nacimiento=fecha_nacimiento,
            genero_original=str(row["genero"]).strip(),
            genero_valor_formulario=genero_valor,
            genero_soportado=genero_soportado,
            telefono=telefono,
            correo=str(row["correo"]).strip(),
            area=str(row["area"]).strip(),
            puesto=str(row["puesto"]).strip(),
            contrato=str(row["contrato"]).strip(),
            sede=str(row["sede"]).strip(),
            fecha_ingreso=fecha_ingreso,
            modalidad=str(row["modalidad"]).strip(),
            warnings=warnings,
        )
        records.append(record)

    return records
