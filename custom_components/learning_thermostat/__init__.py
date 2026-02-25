"""The Learning Thermostat custom component."""
import logging
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .data_collector import DataCollector
from .ml_core import MLCore
from .utils import get_entry_config

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


@dataclass
class LearningThermostatData:
    """Runtime data for the Learning Thermostat integration."""

    data_collector: DataCollector
    ml_core: MLCore
    sensor_entities: list[str]


type LearningThermostatConfigEntry = ConfigEntry[LearningThermostatData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Learning Thermostat component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LearningThermostatConfigEntry) -> bool:
    """Set up Learning Thermostat from a config entry."""
    _LOGGER.info("Setting up Learning Thermostat entry: %s", entry.title)

    # Merged configuration
    config = get_entry_config(entry)

    # --- Find all sensor entities from the selected areas ---
    entity_registry = async_get_entity_registry(hass)
    device_registry = async_get_device_registry(hass)
    
    sensor_entities = set(config.get("include_entities", []))
    area_ids = config.get("areas", [])

    for area_id in area_ids:
        devices_in_area = [
            device.id
            for device in device_registry.devices.values()
            if device.area_id == area_id
        ]
        for entity in entity_registry.entities.values():
            if (
                entity.device_id in devices_in_area
                and entity.domain in ["sensor", "binary_sensor"]
            ):
                sensor_entities.add(entity.entity_id)

    sensor_entities = list(sensor_entities)
    _LOGGER.info("Monitoring sensors: %s", sensor_entities)

    # --- Initialize Data Collector and ML Core ---
    data_path = hass.config.path(f"learning_thermostat_{entry.entry_id}.csv")
    model_path = hass.config.path(f"learning_thermostat_{entry.entry_id}.joblib")

    data_collector = DataCollector(
        hass, config["target_climate_entity"], sensor_entities, data_path
    )
    await data_collector.async_setup()

    ml_core = MLCore(hass, data_path, model_path)
    await ml_core.async_initialize()
    # Trigger initial training in the background
    hass.async_create_background_task(ml_core.async_train_model(), "ml_training")

    entry.runtime_data = LearningThermostatData(
        data_collector=data_collector,
        ml_core=ml_core,
        sensor_entities=sensor_entities,
    )

    # --- Set up the climate platform ---
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add update listener
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LearningThermostatConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Learning Thermostat entry: %s", entry.title)

    # Stop the data collector
    if entry.runtime_data:
        entry.runtime_data.data_collector.stop()

    # Forward the unload to the platform
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
