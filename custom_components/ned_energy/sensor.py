"""Sensor platform for the NED Energy integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    NAME,
    SENSOR_CONSUMPTION,
    SENSOR_EXPORT,
    SENSOR_FOSSIL_PRODUCTION,
    SENSOR_IMPORT,
    SENSOR_RENEWABLE_PERCENTAGE,
    SENSOR_SOLAR_PRODUCTION,
    SENSOR_TOTAL_PRODUCTION,
    SENSOR_WIND_PRODUCTION,
)
from .coordinator import NedEnergyCoordinator, NedEnergyData

# ---------------------------------------------------------------------------
# Entity description
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class NedSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with the coordinator data key."""

    # Key used to look up the value from NedEnergyData.get()
    coordinator_key: str


# ---------------------------------------------------------------------------
# Sensor catalogue
# All energy values are in MWh (hourly granularity from the NED API).
# ---------------------------------------------------------------------------

SENSOR_DESCRIPTIONS: tuple[NedSensorEntityDescription, ...] = (
    # --- Production --------------------------------------------------------
    # NED API returns kWh values; these are per-hour snapshots, not running
    # totals, so we use state_class=MEASUREMENT without device_class=ENERGY
    # (ENERGY device class requires TOTAL/TOTAL_INCREASING and suppresses the
    # unit display when paired with MEASUREMENT).
    NedSensorEntityDescription(
        key="ned_total_production",
        coordinator_key=SENSOR_TOTAL_PRODUCTION,
        name="Total Production",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        suggested_display_precision=0,
    ),
    NedSensorEntityDescription(
        key="ned_solar_production",
        coordinator_key=SENSOR_SOLAR_PRODUCTION,
        name="Solar Production",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
        suggested_display_precision=0,
    ),
    NedSensorEntityDescription(
        key="ned_wind_production",
        coordinator_key=SENSOR_WIND_PRODUCTION,
        name="Wind Production",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wind-turbine",
        suggested_display_precision=0,
    ),
    NedSensorEntityDescription(
        key="ned_fossil_production",
        coordinator_key=SENSOR_FOSSIL_PRODUCTION,
        name="Fossil Gas Production",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-burner",
        suggested_display_precision=0,
    ),
    # --- Consumption -------------------------------------------------------
    NedSensorEntityDescription(
        key="ned_consumption",
        coordinator_key=SENSOR_CONSUMPTION,
        name="Electricity Consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        suggested_display_precision=0,
    ),
    # --- Import / export ---------------------------------------------------
    NedSensorEntityDescription(
        key="ned_import",
        coordinator_key=SENSOR_IMPORT,
        name="Energy Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
        suggested_display_precision=0,
    ),
    NedSensorEntityDescription(
        key="ned_export",
        coordinator_key=SENSOR_EXPORT,
        name="Energy Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
        suggested_display_precision=0,
    ),
    # --- Derived -----------------------------------------------------------
    NedSensorEntityDescription(
        key="ned_renewable_percentage",
        coordinator_key=SENSOR_RENEWABLE_PERCENTAGE,
        name="Renewable Percentage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:leaf",
        suggested_display_precision=1,
    ),
)

# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create all NED Energy sensor entities for a config entry."""
    coordinator: NedEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        NedEnergySensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


# ---------------------------------------------------------------------------
# Entity class
# ---------------------------------------------------------------------------


class NedEnergySensor(CoordinatorEntity[NedEnergyCoordinator], SensorEntity):
    """A single NED Energy grid statistic exposed as a Home Assistant sensor.

    All sensor instances share one coordinator and one device entry so that
    they appear grouped in the HA device registry under "NED Energy".
    """

    entity_description: NedSensorEntityDescription

    # Enables the integration prefix in the entity name, e.g.
    # "NED Energy Solar Production" without hardcoding it per entity.
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NedEnergyCoordinator,
        entry: ConfigEntry,
        description: NedSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        # Stable unique_id that survives renames / restarts
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # All sensors appear under a single "NED Energy" device card
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Nationaal Energiedashboard",
            configuration_url="https://ned.nl",
            entry_type=DeviceEntryType.SERVICE,
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> float | None:
        """Return the sensor value from the coordinator's latest snapshot.

        Returns None (→ "unavailable") when:
        - the coordinator has not completed its first refresh yet, or
        - the API returned None for this specific data point.
        """
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.coordinator_key)

    @property
    def available(self) -> bool:
        """Mark the entity unavailable while the coordinator has no data."""
        return self.coordinator.last_update_success and self.coordinator.data is not None
