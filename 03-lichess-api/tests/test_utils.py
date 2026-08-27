import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import game_result, next_occurrence, parse_weekday  # noqa: E402


def test_game_result_win():
    assert game_result("white", "white") == "win"


def test_game_result_loss():
    assert game_result("black", "white") == "loss"


def test_game_result_draw():
    assert game_result("white", None) == "draw"


def test_parse_weekday_name():
    assert parse_weekday("friday") == 4


def test_parse_weekday_int_passthrough():
    assert parse_weekday(2) == 2


def test_parse_weekday_invalid():
    with pytest.raises(ValueError):
        parse_weekday("someday")


def test_next_occurrence_future_this_week():
    now = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)  # Monday
    result = next_occurrence(3, 18, 0, now)  # Thursday 18:00, later this week
    assert result.weekday() == 3
    assert result > now


def test_next_occurrence_already_passed():
    now = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)  # Friday
    result = next_occurrence(0, 18, 0, now)  # Monday 18:00, earlier this week
    assert result < now
