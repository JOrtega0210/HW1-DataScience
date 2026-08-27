"""Persistencia simple para el modo "resume".

Guarda en un archivo JSON los DNIs registrados exitosamente para poder
saltarlos si el script se vuelve a ejecutar (por ejemplo, tras un corte
a mitad del lote, o corridas programadas en Task Scheduler).
"""

from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, state_file: str):
        self.path = Path(state_file)
        self._dnis: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._dnis = set(data.get("dnis_registrados", []))
            except (json.JSONDecodeError, OSError):
                self._dnis = set()

    def is_registered(self, dni: str) -> bool:
        return dni in self._dnis

    def mark_registered(self, dni: str) -> None:
        self._dnis.add(dni)
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"dnis_registrados": sorted(self._dnis)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
