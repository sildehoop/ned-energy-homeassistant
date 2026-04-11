"""Tests for NedEnergyCoordinator (coordinator.py)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ned_energy.api import (
    NedApiError,
    NedAuthError,
    NedConnectionError,
)
from custom_components.ned_energy.const import (
    SENSOR_CONSUMPTION,
    SENSOR_EXPORT,
    SENSOR_FOSSIL_PRODUCTION,
    SENSOR_IMPORT,
    SENSOR_RENEWABLE_PERCENTAGE,
    SENSOR_SOLAR_PRODUCTION,
    SENSOR_TOTAL_PRODUCTION,
    SENSOR_WIND_PRODUCTION,
)
from custom_components.ned_energy.coordinator import NedEnergyCoordinator, NedEnergyData
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import (
    CONSUMPTION_DATA,
    ENERGY_MIX_DATA,
    IMPORT_EXPORT_DATA,
    PRODUCTION_DATA,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_hass() -> MagicMock:
    hass = MagicMock()
    hass.loop = MagicMock()
    return hass


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_production = AsyncMock(return_value=PRODUCTION_DATA)
    client.get_consumption = AsyncMock(return_value=CONSUMPTION_DATA)
    client.get_import_export = AsyncMock(return_value=IMPORT_EXPORT_DATA)
    client.get_energy_mix = AsyncMock(return_value=ENERGY_MIX_DATA)
    return client


def make_coordinator(
    hass: MagicMock,
    client: MagicMock,
    entry: MagicMock,
) -> NedEnergyCoordinator:
    return NedEnergyCoordinator(hass=hass, client=client, entry=entry)


# ---------------------------------------------------------------------------
# NedEnergyData
# ---------------------------------------------------------------------------


class TestNedEnergyData:
    def test_get_returns_value_from_energy_mix(self) -> None:
        data = NedEnergyData(energy_mix={SENSOR_TOTAL_PRODUCTION: 9000.0})
        assert data.get(SENSOR_TOTAL_PRODUCTION) == 9000.0

    def test_get_returns_value_from_production(self) -> None:
        data = NedEnergyData(production={SENSOR_SOLAR_PRODUCTION: 1500.0})
        assert data.get(SENSOR_SOLAR_PRODUCTION) == 1500.0

    def test_get_returns_value_from_consumption(self) -> None:
        data = NedEnergyData(consumption={SENSOR_CONSUMPTION: 8000.0})
        assert data.get(SENSOR_CONSUMPTION) == 8000.0

    def test_get_returns_value_from_import_export(self) -> None:
        data = NedEnergyData(import_export={SENSOR_IMPORT: 400.0})
        assert data.get(SENSOR_IMPORT) == 400.0

    def test_get_energy_mix_takes_precedence(self) -> None:
        # energy_mix is checked first — its value wins when keys collide
        data = NedEnergyData(
            energy_mix={SENSOR_TOTAL_PRODUCTION: 100.0},
            production={SENSOR_TOTAL_PRODUCTION: 999.0},
        )
        assert data.get(SENSOR_TOTAL_PRODUCTION) == 100.0

    def test_get_returns_none_for_unknown_key(self) -> None:
        data = NedEnergyData()
        assert data.get("nonexistent_sensor") is None


# ---------------------------------------------------------------------------
# Coordinator initialisation
# ---------------------------------------------------------------------------


class TestCoordinatorInit:
    def test_uses_default_scan_interval_when_no_options(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        mock_config_entry.options = {}
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        assert coord.update_interval == timedelta(seconds=300)

    def test_uses_custom_scan_interval_from_options(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        mock_config_entry.options = {"scan_interval": 120}
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        assert coord.update_interval == timedelta(seconds=120)

    def test_stores_config_entry(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        assert coord.config_entry is mock_config_entry


# ---------------------------------------------------------------------------
# _async_update_data — happy path
# ---------------------------------------------------------------------------


class TestAsyncUpdateData:
    @pytest.mark.asyncio
    async def test_returns_ned_energy_data_instance(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        result = await coord._async_update_data()
        assert isinstance(result, NedEnergyData)

    @pytest.mark.asyncio
    async def test_all_four_api_methods_called(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        await coord._async_update_data()

        mock_client.get_production.assert_awaited_once()
        mock_client.get_consumption.assert_awaited_once()
        mock_client.get_import_export.assert_awaited_once()
        mock_client.get_energy_mix.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_data_sections_populated(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        result = await coord._async_update_data()

        assert result.production == PRODUCTION_DATA
        assert result.consumption == CONSUMPTION_DATA
        assert result.import_export == IMPORT_EXPORT_DATA
        assert result.energy_mix == ENERGY_MIX_DATA

    @pytest.mark.asyncio
    async def test_sensor_values_accessible_via_get(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)
        result = await coord._async_update_data()

        assert result.get(SENSOR_TOTAL_PRODUCTION) == 12000.0
        assert result.get(SENSOR_SOLAR_PRODUCTION) == 3000.0
        assert result.get(SENSOR_WIND_PRODUCTION) == 4500.0
        assert result.get(SENSOR_FOSSIL_PRODUCTION) == 4500.0
        assert result.get(SENSOR_CONSUMPTION) == 11500.0
        assert result.get(SENSOR_IMPORT) == 800.0
        assert result.get(SENSOR_EXPORT) == 1300.0
        assert result.get(SENSOR_RENEWABLE_PERCENTAGE) == 62.5


# ---------------------------------------------------------------------------
# _async_update_data — error handling
# ---------------------------------------------------------------------------


class TestAsyncUpdateDataErrors:
    @pytest.mark.asyncio
    async def test_auth_error_raises_config_entry_auth_failed(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        mock_client.get_production = AsyncMock(
            side_effect=NedAuthError("Invalid API key")
        )
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_connection_error_raises_update_failed(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        mock_client.get_production = AsyncMock(
            side_effect=NedConnectionError("timeout")
        )
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Cannot reach NED API"):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_api_error_raises_update_failed(
        self, mock_hass: MagicMock, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        mock_client.get_production = AsyncMock(side_effect=NedApiError("HTTP 503"))
        coord = make_coordinator(mock_hass, mock_client, mock_config_entry)

        with pytest.raises(UpdateFailed, match="NED API error"):
            await coord._async_update_data()
