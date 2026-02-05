"""Tests for the Learning Thermostat climate platform."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry



async def test_climate_unique_id(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that the climate entity has the correct unique ID."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state is not None

    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get("climate.learning_thermostat")
    assert entity is not None
    assert entity.unique_id == mock_config_entry.entry_id
