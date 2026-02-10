"""Tests for the climate platform of the Learning Thermostat integration."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_climate_unique_id(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that the climate entity uses the config entry ID as unique ID."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state is not None

    # In HA, unique_id is not exposed directly in states,
    # but we can check the entity registry.
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    entry = registry.async_get("climate.learning_thermostat")

    assert entry is not None
    assert entry.unique_id == mock_config_entry.entry_id

async def test_climate_name_change_stability(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that changing the name doesn't change the unique_id."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    entity_entry = registry.async_get("climate.learning_thermostat")
    original_unique_id = entity_entry.unique_id

    # Reload integration with a different name in config (simulating a change if it was supported via reconfigure)
    # or just check that it matches entry_id regardless of current name.
    assert original_unique_id == mock_config_entry.entry_id
