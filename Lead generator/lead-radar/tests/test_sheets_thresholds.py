from __future__ import annotations

import importlib

import pytest

from consumer.output import sheets


_ENV_KEYS = (
    "LEAD_RADAR_SHEETS_HOT_FLOOR",
    "LEAD_RADAR_SHEETS_WARM_FLOOR",
    "LEAD_RADAR_SHEETS_OPP_FLOOR",
)


@pytest.fixture(autouse=True)
def _reset_sheets_threshold_env(monkeypatch: pytest.MonkeyPatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    importlib.reload(sheets)
    yield
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    importlib.reload(sheets)


def _reload_sheets(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(sheets)


def test_default_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload_sheets(monkeypatch)

    assert mod.HOT_THRESHOLD == 80
    assert mod.WARM_THRESHOLD == 70
    assert mod.OPP_THRESHOLD == 60


def test_opp_floor_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload_sheets(monkeypatch, LEAD_RADAR_SHEETS_OPP_FLOOR="40")

    assert mod.OPP_THRESHOLD == 40


def test_warm_floor_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload_sheets(monkeypatch, LEAD_RADAR_SHEETS_WARM_FLOOR="60")

    assert mod.WARM_THRESHOLD == 60


def test_hot_floor_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload_sheets(monkeypatch, LEAD_RADAR_SHEETS_HOT_FLOOR="75")

    assert mod.HOT_THRESHOLD == 75


def test_invalid_opp_floor_env_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mod = _reload_sheets(monkeypatch, LEAD_RADAR_SHEETS_OPP_FLOOR="not_a_number")

    assert mod.OPP_THRESHOLD == 60
    assert "LEAD_RADAR_SHEETS_OPP_FLOOR" in caplog.text
    assert "geen geldig getal" in caplog.text


def test_empty_opp_floor_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload_sheets(monkeypatch, LEAD_RADAR_SHEETS_OPP_FLOOR="")

    assert mod.OPP_THRESHOLD == 60
