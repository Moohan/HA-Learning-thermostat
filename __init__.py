"""The Learning Thermostat custom component."""
import logging
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN
from .data_collector import DataCollector
from .ml_core import MLCore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Learning Thermostat component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Learning Thermostat from a config entry."""
    _LOGGER.info("Setting up Learning Thermostat entry: %s", entry.title)

    hass.data[DOMAIN][entry.entry_id] = {}

    # --- Find all sensor entities from the selected areas ---
    entity_registry = async_get_entity_registry(hass)
    device_registry = async_get_device_registry(hass)
    
    sensor_entities = set(entry.data.get("include_entities", []))
    area_ids = entry.data.get("areas", [])

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
    hass.data[DOMAIN][entry.entry_id]["sensor_entities"] = sensor_entities
    _LOGGER.info("Monitoring sensors: %s", sensor_entities)

    # --- Initialize Data Collector and ML Core ---
    data_path = hass.config.path(f"learning_thermostat_{entry.entry_id}.csv")
    model_path = hass.config.path(f"learning_thermostat_{entry.entry_id}.joblib")

    data_collector = DataCollector(
        hass, entry.data["target_climate_entity"], sensor_entities, data_path
    )
    await data_collector.async_setup()

    ml_core = MLCore(hass, data_path, model_path)
    # Trigger initial training in the background
    hass.async_create_task(ml_core.async_train_model())

    hass.data[DOMAIN][entry.entry_id]["data_collector"] = data_collector
    hass.data[DOMAIN][entry.entry_id]["ml_core"] = ml_core

    # --- Set up the climate platform ---
    # The data collector is passed via hass.data
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Learning Thermostat entry: %s", entry.title)

    # Stop the data collector
    data_collector = hass.data[DOMAIN][entry.entry_id].get("data_collector")
    if data_collector:
        data_collector.stop()

    # Forward the unload to the platform
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
