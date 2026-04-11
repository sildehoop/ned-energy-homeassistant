"""Constants for the NED Energy integration."""
from __future__ import annotations

import logging
from datetime import timedelta

DOMAIN = "ned_energy"
NAME = "NED Energy"

# Use a child logger under the homeassistant.components namespace so HA's
# log filtering and the standard "homeassistant.components.<domain>" path
# both work correctly out of the box.
LOGGER = logging.getLogger(f"homeassistant.components.{DOMAIN}")

CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"

API_BASE_URL = "https://api.ned.nl/v1"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=300)  # 5 minutes
MIN_SCAN_INTERVAL = timedelta(seconds=60)   # NED API rate-limit floor
MAX_SCAN_INTERVAL = timedelta(seconds=3600)  # 1 hour ceiling

# NED API point — all sensors use point=0 (Netherlands total)
POINT_NETHERLANDS = 0

# NED API type values (verified working with this API key)
TYPE_ALL = 0
TYPE_WIND = 1
TYPE_SOLAR = 2
TYPE_FOSSIL_GAS = 18       # FossilGasPower
TYPE_ELECTRICITY_MIX = 27  # ElectricityMix (import/export)
TYPE_ELECTRICITY_LOAD = 59 # Electricityload (consumption)

# NED API activity values
ACTIVITY_PROVIDING = 1
ACTIVITY_CONSUMING = 2
ACTIVITY_IMPORT = 3
ACTIVITY_EXPORT = 4

# NED API granularity values (per API docs)
# 3=10min, 4=15min, 5=Hour, 6=Day, 7=Month, 8=Year
GRANULARITY_HOUR = 5
GRANULARITY_15MIN = 4

# NED API granularitytimezone values: 0=UTC, 1=CET (Amsterdam)
GRANULARITY_TIMEZONE = 0

# Sensor keys — used as unique_id suffixes and coordinator data keys
SENSOR_TOTAL_PRODUCTION = "total_production"
SENSOR_SOLAR_PRODUCTION = "solar_production"
SENSOR_WIND_PRODUCTION = "wind_production"
SENSOR_FOSSIL_PRODUCTION = "fossil_production"
SENSOR_CONSUMPTION = "consumption"
SENSOR_IMPORT = "energy_import"
SENSOR_EXPORT = "energy_export"
SENSOR_RENEWABLE_PERCENTAGE = "renewable_percentage"
