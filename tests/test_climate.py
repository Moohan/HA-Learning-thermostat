"""Tests for the climate platform."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_climate_unique_id(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that the climate entity has a stable unique ID based on entry ID."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get("climate.learning_thermostat")

    assert entry is not None
    assert entry.unique_id == f"{mock_config_entry.entry_id}_climate"
