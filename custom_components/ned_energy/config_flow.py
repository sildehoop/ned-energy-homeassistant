"""Config flow for the NED Energy integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import NedAuthError, NedConnectionError, NedEnergyApiClient
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    NAME,
)

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DEFAULT_INTERVAL_SECONDS = int(DEFAULT_SCAN_INTERVAL.total_seconds())
_MIN_INTERVAL_SECONDS = int(MIN_SCAN_INTERVAL.total_seconds())
_MAX_INTERVAL_SECONDS = int(MAX_SCAN_INTERVAL.total_seconds())


def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=_DEFAULT_INTERVAL_SECONDS,
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=_MIN_INTERVAL_SECONDS, max=_MAX_INTERVAL_SECONDS),
            ),
        }
    )


def _options_schema(current_interval: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                vol.Coerce(int),
                vol.Range(min=_MIN_INTERVAL_SECONDS, max=_MAX_INTERVAL_SECONDS),
            ),
        }
    )


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------


class NedEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NED Energy.

    Steps
    -----
    user            — API key + initial scan interval
    reauth_confirm  — replace an expired/invalid API key
    """

    VERSION = 1

    # ------------------------------------------------------------------
    # Step: user (initial setup)
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the API key and optional update interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key: str = user_input[CONF_API_KEY].strip()
            scan_interval: int = user_input[CONF_SCAN_INTERVAL]

            errors = await self._async_validate(api_key)

            if not errors:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=NAME,
                    data={CONF_API_KEY: api_key},
                    options={CONF_SCAN_INTERVAL: scan_interval},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
            description_placeholders={
                "min_interval": str(_MIN_INTERVAL_SECONDS),
                "max_interval": str(_MAX_INTERVAL_SECONDS),
                "default_interval": str(_DEFAULT_INTERVAL_SECONDS),
            },
        )

    # ------------------------------------------------------------------
    # Step: reauth
    # ------------------------------------------------------------------

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Entry point for re-authentication triggered by ConfigEntryAuthFailed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user provide a new API key to restore the integration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key: str = user_input[CONF_API_KEY].strip()

            errors = await self._async_validate(api_key)

            if not errors:
                reauth_entry = self._get_reauth_entry()
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Options flow factory
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NedEnergyOptionsFlow:
        """Return the options flow handler for this entry."""
        return NedEnergyOptionsFlow(config_entry)

    # ------------------------------------------------------------------
    # Shared validation
    # ------------------------------------------------------------------

    async def _async_validate(self, api_key: str) -> dict[str, str]:
        """Validate the API key; return an errors dict (empty = success)."""
        errors: dict[str, str] = {}
        session = async_get_clientsession(self.hass)
        client = NedEnergyApiClient(api_key=api_key, session=session)

        try:
            valid = await client.async_validate_auth()
        except NedAuthError:
            errors[CONF_API_KEY] = "invalid_auth"
        except NedConnectionError:
            errors["base"] = "cannot_connect"
        except aiohttp.ClientError:
            errors["base"] = "cannot_connect"
        except Exception:
            LOGGER.exception("Unexpected error during NED API validation")
            errors["base"] = "unknown"
        else:
            if not valid:
                errors[CONF_API_KEY] = "invalid_auth"

        return errors


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


class NedEnergyOptionsFlow(OptionsFlow):
    """Allow the user to change the update interval after initial setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the current interval so the form can pre-fill it."""
        self._current_interval: int = config_entry.options.get(
            CONF_SCAN_INTERVAL, _DEFAULT_INTERVAL_SECONDS
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options form pre-filled with the current interval."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self._current_interval),
            description_placeholders={
                "min_interval": str(_MIN_INTERVAL_SECONDS),
                "max_interval": str(_MAX_INTERVAL_SECONDS),
            },
        )
