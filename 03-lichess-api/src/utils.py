import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def setup_logging(log_file: Path, name: str) -> logging.Logger:
    """Configure the root logger so every module (including api_client) writes
    to the same log file/console, then return a named child logger for the caller."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)

    return logging.getLogger(name)


def game_result(color: str, winner: Optional[str]) -> str:
    if winner is None:
        return "draw"
    return "win" if winner == color else "loss"


def parse_weekday(value) -> int:
    if isinstance(value, int):
        return value
    key = str(value).strip().lower()
    if key not in WEEKDAYS:
        raise ValueError(f"Invalid weekday: {value}")
    return WEEKDAYS[key]


def next_occurrence(weekday: int, hour: int, minute: int, now: datetime) -> datetime:
    """Return this week's datetime for the given weekday/time (UTC), which may be in the past."""
    days_ahead = weekday - now.weekday()
    candidate = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return candidate
