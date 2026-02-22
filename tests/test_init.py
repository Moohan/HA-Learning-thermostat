"""Test the learning_thermostat integration."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry



async def test_setup_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that the integration loads."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry.runtime_data is not None
    assert hass.states.get("climate.learning_thermostat") is not None
