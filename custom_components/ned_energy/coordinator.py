"""DataUpdateCoordinator for the NED Energy integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    EnergyMixData,
    NedApiError,
    NedAuthError,
    NedConnectionError,
    NedEnergyApiClient,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)

# NedEnergyData is just the flat EnergyMixData dict; expose it as a type alias
# so sensor.py can still import it by name.
NedEnergyData = EnergyMixData


class NedEnergyCoordinator(DataUpdateCoordinator[NedEnergyData]):
    """Polls the NED API every 5 minutes and stores a flat energy snapshot.

    Consumers (sensor entities) access data via ``coordinator.data.get(key)``
    using the SENSOR_* keys from const.py.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: NedEnergyApiClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the coordinator with the HA instance, API client and config entry."""
        interval = timedelta(
            seconds=entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
            )
        )
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=interval,
        )
        self.config_entry = entry
        self._client = client

    # ------------------------------------------------------------------
    # Core update method — called by the coordinator framework
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> NedEnergyData:
        """Fetch all NED data in one call and return a flat snapshot."""
        try:
            data = await self._client.get_energy_mix()
        except NedAuthError as err:
            # Tells HA to surface a re-auth notification in the UI.
            raise ConfigEntryAuthFailed(err) from err
        except NedConnectionError as err:
            raise UpdateFailed(f"Cannot reach NED API: {err}") from err
        except NedApiError as err:
            raise UpdateFailed(f"NED API error: {err}") from err

        LOGGER.debug("NED coordinator refresh complete — %s", data)
        return data
