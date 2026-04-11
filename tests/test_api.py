"""Tests for NED Energy API client (api.py)."""
from __future__ import annotations

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ned_energy.api import (
    NedApiError,
    NedAuthError,
    NedConnectionError,
    NedEnergyApiClient,
    _calc_renewable_pct,
    _latest_volume,
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

from .conftest import (
    API_KEY,
    CONSUMPTION_DATA,
    ENERGY_MIX_DATA,
    IMPORT_EXPORT_DATA,
    PRODUCTION_DATA,
    empty_utilization_response,
    make_mock_response,
    utilization_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_client(session: MagicMock) -> NedEnergyApiClient:
    return NedEnergyApiClient(api_key=API_KEY, session=session)


# ---------------------------------------------------------------------------
# Pure function tests (no I/O)
# ---------------------------------------------------------------------------


class TestLatestVolume:
    def test_returns_volume_from_first_member(self) -> None:
        members = [{"volume": 1234.5}, {"volume": 999.0}]
        assert _latest_volume(members) == 1234.5

    def test_returns_none_for_empty_list(self) -> None:
        assert _latest_volume([]) is None

    def test_returns_none_when_volume_key_missing(self) -> None:
        assert _latest_volume([{"other": "field"}]) is None


class TestCalcRenewablePct:
    def test_calculates_correctly(self) -> None:
        data = {
            SENSOR_TOTAL_PRODUCTION: 10000.0,
            SENSOR_SOLAR_PRODUCTION: 2000.0,
            SENSOR_WIND_PRODUCTION: 3000.0,
        }
        assert _calc_renewable_pct(data) == 50.0

    def test_rounds_to_one_decimal(self) -> None:
        data = {
            SENSOR_TOTAL_PRODUCTION: 3000.0,
            SENSOR_SOLAR_PRODUCTION: 1000.0,
            SENSOR_WIND_PRODUCTION: 1000.0,
        }
        assert _calc_renewable_pct(data) == 66.7

    def test_returns_none_when_total_is_zero(self) -> None:
        data = {
            SENSOR_TOTAL_PRODUCTION: 0.0,
            SENSOR_SOLAR_PRODUCTION: 0.0,
            SENSOR_WIND_PRODUCTION: 0.0,
        }
        assert _calc_renewable_pct(data) is None

    def test_returns_none_when_any_value_is_none(self) -> None:
        data = {
            SENSOR_TOTAL_PRODUCTION: 10000.0,
            SENSOR_SOLAR_PRODUCTION: None,
            SENSOR_WIND_PRODUCTION: 3000.0,
        }
        assert _calc_renewable_pct(data) is None

    def test_returns_none_when_keys_missing(self) -> None:
        assert _calc_renewable_pct({}) is None


# ---------------------------------------------------------------------------
# async_validate_auth
# ---------------------------------------------------------------------------


class TestValidateAuth:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(200, utilization_response(100.0))
        )
        client = make_client(session)
        assert await client.async_validate_auth() is True

    @pytest.mark.asyncio
    async def test_returns_false_on_401(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(HTTPStatus.UNAUTHORIZED, text_data="Unauthorized")
        )
        client = make_client(session)
        assert await client.async_validate_auth() is False

    @pytest.mark.asyncio
    async def test_returns_false_on_403(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(HTTPStatus.FORBIDDEN, text_data="Forbidden")
        )
        client = make_client(session)
        assert await client.async_validate_auth() is False


# ---------------------------------------------------------------------------
# get_production
# ---------------------------------------------------------------------------


class TestGetProduction:
    @pytest.mark.asyncio
    async def test_returns_all_production_keys(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(200, utilization_response(5000.0))
        )
        client = make_client(session)
        result = await client.get_production()

        assert SENSOR_TOTAL_PRODUCTION in result
        assert SENSOR_SOLAR_PRODUCTION in result
        assert SENSOR_WIND_PRODUCTION in result
        assert SENSOR_FOSSIL_PRODUCTION in result

    @pytest.mark.asyncio
    async def test_volume_extracted_correctly(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(200, utilization_response(9876.0))
        )
        client = make_client(session)
        result = await client.get_production()

        assert result[SENSOR_TOTAL_PRODUCTION] == 9876.0

    @pytest.mark.asyncio
    async def test_none_returned_for_empty_response(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(200, empty_utilization_response())
        )
        client = make_client(session)
        result = await client.get_production()

        assert result[SENSOR_TOTAL_PRODUCTION] is None

    @pytest.mark.asyncio
    async def test_api_error_stored_as_none(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(500, text_data="Internal Server Error")
        )
        client = make_client(session)
        result = await client.get_production()

        # NedApiError is caught per-key; value is None rather than raising
        assert result[SENSOR_TOTAL_PRODUCTION] is None


# ---------------------------------------------------------------------------
# get_consumption
# ---------------------------------------------------------------------------


class TestGetConsumption:
    @pytest.mark.asyncio
    async def test_returns_consumption_key(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(200, utilization_response(11000.0))
        )
        client = make_client(session)
        result = await client.get_consumption()

        assert SENSOR_CONSUMPTION in result
        assert result[SENSOR_CONSUMPTION] == 11000.0


# ---------------------------------------------------------------------------
# get_import_export
# ---------------------------------------------------------------------------


class TestGetImportExport:
    @pytest.mark.asyncio
    async def test_returns_import_and_export_keys(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(200, utilization_response(500.0))
        )
        client = make_client(session)
        result = await client.get_import_export()

        assert SENSOR_IMPORT in result
        assert SENSOR_EXPORT in result


# ---------------------------------------------------------------------------
# get_energy_mix
# ---------------------------------------------------------------------------


class TestGetEnergyMix:
    @pytest.mark.asyncio
    async def test_combines_all_sections(self) -> None:
        client = make_client(MagicMock())
        client.get_production = AsyncMock(return_value=PRODUCTION_DATA)
        client.get_consumption = AsyncMock(return_value=CONSUMPTION_DATA)
        client.get_import_export = AsyncMock(return_value=IMPORT_EXPORT_DATA)

        result = await client.get_energy_mix()

        assert result[SENSOR_TOTAL_PRODUCTION] == 12000.0
        assert result[SENSOR_CONSUMPTION] == 11500.0
        assert result[SENSOR_IMPORT] == 800.0
        assert result[SENSOR_EXPORT] == 1300.0

    @pytest.mark.asyncio
    async def test_renewable_percentage_derived(self) -> None:
        client = make_client(MagicMock())
        client.get_production = AsyncMock(return_value=PRODUCTION_DATA)
        client.get_consumption = AsyncMock(return_value=CONSUMPTION_DATA)
        client.get_import_export = AsyncMock(return_value=IMPORT_EXPORT_DATA)

        result = await client.get_energy_mix()

        # (3000 + 4500) / 12000 * 100 = 62.5
        assert result[SENSOR_RENEWABLE_PERCENTAGE] == 62.5

    @pytest.mark.asyncio
    async def test_renewable_percentage_none_when_no_total(self) -> None:
        client = make_client(MagicMock())
        client.get_production = AsyncMock(
            return_value={**PRODUCTION_DATA, SENSOR_TOTAL_PRODUCTION: None}
        )
        client.get_consumption = AsyncMock(return_value=CONSUMPTION_DATA)
        client.get_import_export = AsyncMock(return_value=IMPORT_EXPORT_DATA)

        result = await client.get_energy_mix()

        assert result[SENSOR_RENEWABLE_PERCENTAGE] is None


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------


class TestHttpErrors:
    @pytest.mark.asyncio
    async def test_401_raises_ned_auth_error(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(HTTPStatus.UNAUTHORIZED, text_data="Unauthorized")
        )
        client = make_client(session)

        with pytest.raises(NedAuthError):
            await client._fetch_utilization(
                point=0, activity_type=1, activity=1
            )

    @pytest.mark.asyncio
    async def test_403_raises_ned_auth_error(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(HTTPStatus.FORBIDDEN, text_data="Forbidden")
        )
        client = make_client(session)

        with pytest.raises(NedAuthError):
            await client._fetch_utilization(
                point=0, activity_type=1, activity=1
            )

    @pytest.mark.asyncio
    async def test_500_raises_ned_api_error(self) -> None:
        session = MagicMock()
        session.get = MagicMock(
            return_value=make_mock_response(500, text_data="Internal Server Error")
        )
        client = make_client(session)

        with pytest.raises(NedApiError):
            await client._fetch_utilization(
                point=0, activity_type=1, activity=1
            )

    @pytest.mark.asyncio
    async def test_timeout_raises_ned_connection_error(self) -> None:
        import aiohttp

        session = MagicMock()
        session.get = MagicMock(side_effect=aiohttp.ServerTimeoutError())
        client = make_client(session)

        with pytest.raises(NedConnectionError):
            await client._fetch_utilization(
                point=0, activity_type=1, activity=1
            )

    @pytest.mark.asyncio
    async def test_client_error_raises_ned_connection_error(self) -> None:
        import aiohttp

        session = MagicMock()
        session.get = MagicMock(side_effect=aiohttp.ClientConnectionError("refused"))
        client = make_client(session)

        with pytest.raises(NedConnectionError):
            await client._fetch_utilization(
                point=0, activity_type=1, activity=1
            )
