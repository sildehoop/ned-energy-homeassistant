"""Tests for NED Energy sensor entities (sensor.py)."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.ned_energy.const import (
    DOMAIN,
    SENSOR_CONSUMPTION,
    SENSOR_EXPORT,
    SENSOR_IMPORT,
    SENSOR_RENEWABLE_PERCENTAGE,
    SENSOR_SOLAR_PRODUCTION,
    SENSOR_TOTAL_PRODUCTION,
)
from custom_components.ned_energy.coordinator import NedEnergyData
from custom_components.ned_energy.sensor import (
    SENSOR_DESCRIPTIONS,
    NedEnergySensor,
    NedSensorEntityDescription,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfEnergy

from .conftest import ENERGY_MIX_DATA, ENTRY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_coordinator(
    data: NedEnergyData | None = None, success: bool = True
) -> MagicMock:
    coord = MagicMock()
    coord.data = data
    coord.last_update_success = success
    return coord


def make_sensor(
    coordinator_key: str,
    entity_key: str = "ned_test",
    data: NedEnergyData | None = None,
    success: bool = True,
    entry_id: str = ENTRY_ID,
) -> NedEnergySensor:
    coord = make_coordinator(data=data, success=success)
    entry = MagicMock()
    entry.entry_id = entry_id

    description = NedSensorEntityDescription(
        key=entity_key,
        coordinator_key=coordinator_key,
        name="Test Sensor",
    )
    sensor = NedEnergySensor(coord, entry, description)
    return sensor


# ---------------------------------------------------------------------------
# SENSOR_DESCRIPTIONS catalogue
# ---------------------------------------------------------------------------


class TestSensorDescriptions:
    EXPECTED_KEYS = {
        "ned_total_production",
        "ned_solar_production",
        "ned_wind_production",
        "ned_fossil_production",
        "ned_consumption",
        "ned_import",
        "ned_export",
        "ned_renewable_percentage",
    }

    def test_all_required_sensors_present(self) -> None:
        keys = {d.key for d in SENSOR_DESCRIPTIONS}
        assert keys == self.EXPECTED_KEYS

    def test_energy_sensors_have_mwh_unit(self) -> None:
        energy_keys = self.EXPECTED_KEYS - {"ned_renewable_percentage"}
        for desc in SENSOR_DESCRIPTIONS:
            if desc.key in energy_keys:
                assert desc.native_unit_of_measurement == UnitOfEnergy.MEGA_WATT_HOUR, (
                    f"{desc.key} should use MWh"
                )

    def test_renewable_percentage_uses_percent_unit(self) -> None:
        desc = next(
            d for d in SENSOR_DESCRIPTIONS if d.key == "ned_renewable_percentage"
        )
        assert desc.native_unit_of_measurement == PERCENTAGE

    def test_energy_sensors_have_energy_device_class(self) -> None:
        energy_keys = self.EXPECTED_KEYS - {"ned_renewable_percentage"}
        for desc in SENSOR_DESCRIPTIONS:
            if desc.key in energy_keys:
                assert desc.device_class == SensorDeviceClass.ENERGY, (
                    f"{desc.key} should have ENERGY device class"
                )

    def test_all_sensors_are_measurement_state_class(self) -> None:
        for desc in SENSOR_DESCRIPTIONS:
            assert desc.state_class == SensorStateClass.MEASUREMENT, (
                f"{desc.key} should have MEASUREMENT state class"
            )

    def test_coordinator_key_set_on_every_description(self) -> None:
        for desc in SENSOR_DESCRIPTIONS:
            assert desc.coordinator_key, f"{desc.key} is missing coordinator_key"


# ---------------------------------------------------------------------------
# NedEnergySensor.native_value
# ---------------------------------------------------------------------------


class TestNativeValue:
    def test_returns_value_from_coordinator_data(self) -> None:
        ned_data = NedEnergyData(energy_mix={SENSOR_TOTAL_PRODUCTION: 9500.0})
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, data=ned_data)
        assert sensor.native_value == 9500.0

    def test_returns_none_when_coordinator_data_is_none(self) -> None:
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, data=None)
        assert sensor.native_value is None

    def test_returns_none_when_key_not_in_data(self) -> None:
        ned_data = NedEnergyData()  # all sections empty
        sensor = make_sensor("nonexistent_key", data=ned_data)
        assert sensor.native_value is None

    def test_solar_production_value(self) -> None:
        ned_data = NedEnergyData(energy_mix=ENERGY_MIX_DATA)
        sensor = make_sensor(SENSOR_SOLAR_PRODUCTION, data=ned_data)
        assert sensor.native_value == 3000.0

    def test_renewable_percentage_value(self) -> None:
        ned_data = NedEnergyData(energy_mix=ENERGY_MIX_DATA)
        sensor = make_sensor(SENSOR_RENEWABLE_PERCENTAGE, data=ned_data)
        assert sensor.native_value == 62.5

    def test_consumption_value(self) -> None:
        ned_data = NedEnergyData(consumption={SENSOR_CONSUMPTION: 11500.0})
        sensor = make_sensor(SENSOR_CONSUMPTION, data=ned_data)
        assert sensor.native_value == 11500.0

    def test_import_value(self) -> None:
        ned_data = NedEnergyData(import_export={SENSOR_IMPORT: 800.0})
        sensor = make_sensor(SENSOR_IMPORT, data=ned_data)
        assert sensor.native_value == 800.0

    def test_export_value(self) -> None:
        ned_data = NedEnergyData(import_export={SENSOR_EXPORT: 1300.0})
        sensor = make_sensor(SENSOR_EXPORT, data=ned_data)
        assert sensor.native_value == 1300.0


# ---------------------------------------------------------------------------
# NedEnergySensor.available
# ---------------------------------------------------------------------------


class TestAvailability:
    def test_available_when_data_present_and_update_success(self) -> None:
        ned_data = NedEnergyData(energy_mix=ENERGY_MIX_DATA)
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, data=ned_data, success=True)
        assert sensor.available is True

    def test_unavailable_when_data_is_none(self) -> None:
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, data=None, success=True)
        assert sensor.available is False

    def test_unavailable_when_last_update_failed(self) -> None:
        ned_data = NedEnergyData(energy_mix=ENERGY_MIX_DATA)
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, data=ned_data, success=False)
        assert sensor.available is False

    def test_unavailable_when_both_data_none_and_update_failed(self) -> None:
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, data=None, success=False)
        assert sensor.available is False


# ---------------------------------------------------------------------------
# NedEnergySensor metadata
# ---------------------------------------------------------------------------


class TestSensorMetadata:
    def test_unique_id_format(self) -> None:
        ned_data = NedEnergyData()
        sensor = make_sensor(
            SENSOR_TOTAL_PRODUCTION,
            entity_key="ned_total_production",
            data=ned_data,
            entry_id="my_entry",
        )
        assert sensor._attr_unique_id == "my_entry_ned_total_production"

    def test_has_entity_name_enabled(self) -> None:
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION)
        assert sensor._attr_has_entity_name is True

    def test_device_info_uses_domain_and_entry_id(self) -> None:
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION, entry_id="abc123")
        assert (DOMAIN, "abc123") in sensor._attr_device_info["identifiers"]

    def test_device_info_configuration_url(self) -> None:
        sensor = make_sensor(SENSOR_TOTAL_PRODUCTION)
        assert sensor._attr_device_info["configuration_url"] == "https://ned.nl"
