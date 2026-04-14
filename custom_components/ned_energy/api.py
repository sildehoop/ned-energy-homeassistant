"""Async API client for the NED (Nationaal Energiedashboard) API."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

import aiohttp

from .const import (
    ACTIVITY_CONSUMING,
    ACTIVITY_EXPORT,
    ACTIVITY_IMPORT,
    ACTIVITY_PROVIDING,
    API_BASE_URL,
    GRANULARITY_HOUR,
    GRANULARITY_TIMEZONE,
    LOGGER,
    POINT_NETHERLANDS,
    SENSOR_CONSUMPTION,
    SENSOR_EXPORT,
    SENSOR_FOSSIL_PRODUCTION,
    SENSOR_IMPORT,
    SENSOR_RENEWABLE_PERCENTAGE,
    SENSOR_SOLAR_PRODUCTION,
    SENSOR_TOTAL_PRODUCTION,
    SENSOR_WIND_PRODUCTION,
    TYPE_ALL,
    TYPE_ELECTRICITY_LOAD,
    TYPE_ELECTRICITY_MIX,
    TYPE_FOSSIL_GAS,
    TYPE_SOLAR,
    TYPE_WIND,
)

# Per-request timeout shared by all calls (seconds).
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NedApiError(Exception):
    """Raised for any non-auth NED API failure."""


class NedAuthError(NedApiError):
    """Raised when the API key is rejected (HTTP 401/403)."""


class NedConnectionError(NedApiError):
    """Raised when the network request cannot be completed."""


# ---------------------------------------------------------------------------
# Result dataclasses (typed dicts keep coordinator code clean)
# ---------------------------------------------------------------------------

ProductionData = dict[str, float | None]
ConsumptionData = dict[str, float | None]
ImportExportData = dict[str, float | None]
EnergyMixData = dict[str, float | None]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class NedEnergyApiClient:
    """Async client for the NED Energy API.

    All public methods are coroutines and safe to call from the HA event loop.
    The caller is responsible for providing and managing the aiohttp session
    (use ``homeassistant.helpers.aiohttp_client.async_get_clientsession``).
    """

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialise with an API key and a shared aiohttp session."""
        self._api_key = api_key
        self._session = session

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def async_validate_auth(self) -> bool:
        """Return True if the API key can access the /utilizations endpoint.

        Tests the same endpoint used by the coordinator so that subscription-level
        403 errors (key valid but no data access) are caught during config flow
        validation instead of silently passing and failing on first refresh.
        Uses date-only format for validfrom filters: the NED API returns 403 for
        datetime strings on lower subscription tiers.
        """
        now = datetime.now(tz=UTC)
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        params = {
            "point": POINT_NETHERLANDS,
            "type": TYPE_ALL,
            "activity": ACTIVITY_PROVIDING,
            "granularity": GRANULARITY_HOUR,
            "granularitytimezone": GRANULARITY_TIMEZONE,
            "classification": 2,
            "validfrom[after]": yesterday,
            "validfrom[strictly_before]": tomorrow,
            "itemsPerPage": 1,
            "order[validfrom]": "desc",
        }
        headers = {
            "X-AUTH-TOKEN": self._api_key,
            "Accept": "application/ld+json",
            "User-Agent": "HomeAssistant/NED-Energy-Integration",
        }
        try:
            async with self._session.get(
                f"{API_BASE_URL}/utilizations",
                params=params,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            ) as response:
                if response.status in (401, 403):
                    return False
                return response.status < 500
        except (TimeoutError, aiohttp.ClientError) as err:
            raise NedConnectionError("Connection error during auth validation") from err

    # ------------------------------------------------------------------
    # Domain-level public methods
    # ------------------------------------------------------------------

    async def get_production(self) -> ProductionData:
        """Return the latest grid production figures (kWh).

        Keys: total_production, solar_production, wind_production,
              fossil_production.
        """
        # (sensor_key, type, activity)
        queries: list[tuple[str, int, int]] = [
            (SENSOR_TOTAL_PRODUCTION, TYPE_ALL, ACTIVITY_PROVIDING),
            (SENSOR_SOLAR_PRODUCTION, TYPE_SOLAR, ACTIVITY_PROVIDING),
            (SENSOR_WIND_PRODUCTION, TYPE_WIND, ACTIVITY_PROVIDING),
            (SENSOR_FOSSIL_PRODUCTION, TYPE_FOSSIL_GAS, ACTIVITY_PROVIDING),
        ]
        return await self._fetch_multi(queries)

    async def get_consumption(self) -> ConsumptionData:
        """Return the latest national electricity consumption figure (kWh).

        Keys: consumption.
        """
        queries: list[tuple[str, int, int]] = [
            (SENSOR_CONSUMPTION, TYPE_ELECTRICITY_LOAD, ACTIVITY_CONSUMING),
        ]
        return await self._fetch_multi(queries)

    async def get_import_export(self) -> ImportExportData:
        """Return the latest cross-border import and export figures (kWh).

        Keys: energy_import, energy_export.
        """
        queries: list[tuple[str, int, int]] = [
            (SENSOR_IMPORT, TYPE_ELECTRICITY_MIX, ACTIVITY_IMPORT),
            (SENSOR_EXPORT, TYPE_ELECTRICITY_MIX, ACTIVITY_EXPORT),
        ]
        return await self._fetch_multi(queries)

    async def get_energy_mix(self) -> EnergyMixData:
        """Return a combined snapshot of production, consumption, import/export.

        Includes a derived renewable percentage. This is the main method used
        by the coordinator's ``_async_update_data``.
        """
        production, consumption, import_export = await asyncio.gather(
            self.get_production(),
            self.get_consumption(),
            self.get_import_export(),
        )

        data: EnergyMixData = {**production, **consumption, **import_export}
        data[SENSOR_RENEWABLE_PERCENTAGE] = _calc_renewable_pct(data)

        LOGGER.debug("NED energy mix snapshot: %s", data)
        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_multi(
        self,
        queries: list[tuple[str, int, int]],
    ) -> dict[str, float | None]:
        """Fetch multiple utilization queries in parallel."""

        async def _fetch_one(
            sensor_key: str, activity_type: int, activity: int
        ) -> tuple[str, float | None]:
            try:
                members = await self._fetch_utilization(
                    point=POINT_NETHERLANDS,
                    activity_type=activity_type,
                    activity=activity,
                )
                volume = _latest_volume(members)
                LOGGER.debug("NED [%s] = %s MWh", sensor_key, volume)
                return sensor_key, volume
            except NedAuthError:
                # Re-raise so the coordinator receives ConfigEntryAuthFailed
                # and HA shows the re-authentication notification in the UI.
                raise
            except NedApiError as err:
                LOGGER.warning("Failed to fetch '%s': %s", sensor_key, err)
                return sensor_key, None

        pairs = await asyncio.gather(*(_fetch_one(*q) for q in queries))
        return dict(pairs)

    async def _fetch_utilization(
        self,
        point: int,
        activity_type: int,
        activity: int,
        items_per_page: int = 2,
    ) -> list[dict[str, Any]]:
        """Perform a GET /utilizations request and return the member list.

        Fetches 2 records by default so that _latest_volume() can skip the
        current incomplete hour and fall back to the previous completed hour.
        The NED API returns 403 for datetime strings in validfrom filters on
        lower subscription tiers, so date-only format is used here; the
        current-hour exclusion is handled in _latest_volume() instead.
        """
        now = datetime.now(tz=UTC)
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        params: dict[str, Any] = {
            "point": point,
            "type": activity_type,
            "activity": activity,
            "granularity": GRANULARITY_HOUR,
            "granularitytimezone": GRANULARITY_TIMEZONE,
            "classification": 2,  # actual data, not forecast
            "validfrom[after]": yesterday,
            # Date-only format required: datetime strings cause HTTP 403 on
            # lower NED API subscription tiers.
            "validfrom[strictly_before]": tomorrow,
            "itemsPerPage": items_per_page,
            "order[validfrom]": "desc",
        }
        headers = {
            "X-AUTH-TOKEN": self._api_key,
            "Accept": "application/ld+json",
            "User-Agent": "HomeAssistant/NED-Energy-Integration",
        }

        url = f"{API_BASE_URL}/utilizations"

        try:
            async with self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            ) as response:
                await self._raise_for_status(response)
                payload: dict[str, Any] = await response.json(content_type=None)
        except (NedApiError, NedAuthError):
            raise
        except TimeoutError as err:
            raise NedConnectionError("Request to NED API timed out") from err
        except aiohttp.ClientError as err:
            raise NedConnectionError(f"Connection error: {err}") from err

        return payload.get("hydra:member", [])

    @staticmethod
    async def _raise_for_status(response: aiohttp.ClientResponse) -> None:
        """Translate HTTP error codes into typed exceptions."""
        if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise NedAuthError(
                f"Authentication failed (HTTP {response.status}). "
                "Check your NED API key."
            )
        if response.status != HTTPStatus.OK:
            body = await response.text()
            raise NedApiError(
                f"Unexpected HTTP {response.status} from NED API: {body[:200]}"
            )


# ---------------------------------------------------------------------------
# Pure functions (no I/O — easy to unit-test)
# ---------------------------------------------------------------------------


def _latest_volume(members: list[dict[str, Any]]) -> float | None:
    """Return the volume (MWh) from the most recent *completed* utilization member.

    Near-realtime data for the current running hour is continuously revised,
    causing an oscillating (sawtooth) pattern on sensor history graphs.
    We skip any member whose validfrom falls within the current UTC hour so
    that only stable, completed-hour values are returned.
    """
    current_hour_utc = datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)

    for member in members:
        validfrom_str = member.get("validfrom")
        if validfrom_str:
            try:
                vf = datetime.fromisoformat(validfrom_str)
                if vf.utcoffset() is None:
                    vf = vf.replace(tzinfo=UTC)
                if vf >= current_hour_utc:
                    continue  # skip incomplete current hour
            except (ValueError, TypeError):
                pass
        raw = member.get("volume")
        return float(raw) if raw is not None else None
    return None


def _calc_renewable_pct(data: dict[str, Any]) -> float | None:
    """Derive renewable percentage from solar + wind vs total production."""
    total = data.get(SENSOR_TOTAL_PRODUCTION)
    solar = data.get(SENSOR_SOLAR_PRODUCTION)
    wind = data.get(SENSOR_WIND_PRODUCTION)
    if None in (total, solar, wind) or total == 0:
        return None
    return round((solar + wind) / total * 100, 1)  # type: ignore[operator]
