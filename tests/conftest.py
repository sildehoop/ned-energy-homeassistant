"""Shared pytest fixtures for the NED Energy integration tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Raw API response helpers
# ---------------------------------------------------------------------------

ENTRY_ID = "test_entry_id"
API_KEY = "test-api-key-1234"


def utilization_response(volume: float) -> dict[str, Any]:
    """Build a minimal /utilizations hydra response with one member."""
    return {
        "hydra:totalItems": 1,
        "hydra:member": [
            {
                "volume": volume,
                "validfrom": "2024-01-15T10:00:00+01:00",
                "validto": "2024-01-15T11:00:00+01:00",
            }
        ],
    }


def empty_utilization_response() -> dict[str, Any]:
    """Build a /utilizations response with no data."""
    return {"hydra:totalItems": 0, "hydra:member": []}


# ---------------------------------------------------------------------------
# Canonical data fixture returned by every successful API call
# ---------------------------------------------------------------------------

PRODUCTION_DATA: dict[str, float | None] = {
    "total_production": 12000.0,
    "solar_production": 3000.0,
    "wind_production": 4500.0,
    "fossil_production": 4500.0,
}

CONSUMPTION_DATA: dict[str, float | None] = {
    "consumption": 11500.0,
}

IMPORT_EXPORT_DATA: dict[str, float | None] = {
    "energy_import": 800.0,
    "energy_export": 1300.0,
}

ENERGY_MIX_DATA: dict[str, float | None] = {
    **PRODUCTION_DATA,
    **CONSUMPTION_DATA,
    **IMPORT_EXPORT_DATA,
    "renewable_percentage": 62.5,  # (3000 + 4500) / 12000 * 100
}


# ---------------------------------------------------------------------------
# Mock aiohttp session
# ---------------------------------------------------------------------------


def make_mock_response(
    status: int = 200,
    json_data: dict[str, Any] | None = None,
    text_data: str = "",
) -> MagicMock:
    """Return a mock aiohttp response usable as an async context manager."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data or {})
    response.text = AsyncMock(return_value=text_data)

    # Support  `async with session.get(...) as response:`
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a mock aiohttp.ClientSession with a configurable get() response."""
    session = MagicMock()
    session.get = MagicMock(
        return_value=make_mock_response(
            status=200,
            json_data=utilization_response(12000.0),
        )
    )
    return session


# ---------------------------------------------------------------------------
# Mock config entry
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Return a minimal mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = ENTRY_ID
    entry.data = {"api_key": API_KEY}
    entry.options = {}
    return entry
