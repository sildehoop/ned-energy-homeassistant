"""The NED Energy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NedEnergyApiClient
from .const import CONF_API_KEY, DOMAIN, LOGGER
from .coordinator import NedEnergyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_REFRESH = "refresh_data"


# ---------------------------------------------------------------------------
# Entry lifecycle
# ---------------------------------------------------------------------------


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a NED Energy config entry.

    Sequence
    --------
    1. Build the API client from stored credentials.
    2. Create the coordinator and attempt the first data refresh.
       Raises ConfigEntryNotReady on failure so HA retries automatically.
    3. Store the coordinator in hass.data for sensor platform access.
    4. Forward setup to all platforms (sensor).
    5. Register the ned_energy.refresh service (once, guarded by has_service).
    6. Register an options-change listener so a new scan interval takes effect
       immediately without a manual restart.
    """
    # 1 — API client
    client = NedEnergyApiClient(
        api_key=entry.data[CONF_API_KEY],
        session=async_get_clientsession(hass),
    )

    # 2 — Coordinator + first refresh
    coordinator = NedEnergyCoordinator(hass=hass, client=client, entry=entry)
    await coordinator.async_config_entry_first_refresh()

    # 3 — Store coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 4 — Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 5 — Service registration (single instance across all entries)
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):

        async def _handle_refresh(call: ServiceCall) -> None:
            """Force an immediate poll for every active NED Energy coordinator."""
            for coord in hass.data.get(DOMAIN, {}).values():
                await coord.async_request_refresh()

        hass.services.async_register(DOMAIN, SERVICE_REFRESH, _handle_refresh)
        LOGGER.debug("Registered service %s.%s", DOMAIN, SERVICE_REFRESH)

    # 6 — Options listener — unregistered automatically on unload
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a NED Energy config entry.

    Tears down platforms, removes the coordinator from hass.data, and
    removes the shared service when the last entry is unloaded.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        LOGGER.debug("Unloaded NED Energy entry %s", entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
            LOGGER.debug("Removed service %s.%s", DOMAIN, SERVICE_REFRESH)

    return unload_ok


# ---------------------------------------------------------------------------
# Options change listener
# ---------------------------------------------------------------------------


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change (e.g. a new scan interval).

    HA calls this whenever the user saves from the Options flow. A full reload
    rebuilds the coordinator with the updated update_interval so the change
    takes effect immediately.
    """
    LOGGER.debug(
        "NED Energy options updated for entry %s — reloading", entry.entry_id
    )
    await hass.config_entries.async_reload(entry.entry_id)
