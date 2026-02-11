"""Tests for the Learning Thermostat climate platform."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_unique_id_stability(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that the unique_id is stable across entity renames."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get("climate.learning_thermostat")
    assert entry is not None

    # Initial unique_id should be the entry_id
    assert entry.unique_id == mock_config_entry.entry_id

    # Rename the entity
    ent_reg.async_update_entity("climate.learning_thermostat", name="New Name")
    await hass.async_block_till_done()

    entry = ent_reg.async_get("climate.learning_thermostat")
    assert entry.name == "New Name"
    # unique_id should still be the same entry_id
    assert entry.unique_id == mock_config_entry.entry_id

    # Change the config entry title
    hass.config_entries.async_update_entry(mock_config_entry, title="New Title")
    await hass.async_block_till_done()

    entry = ent_reg.async_get("climate.learning_thermostat")
    assert entry.unique_id == mock_config_entry.entry_id
