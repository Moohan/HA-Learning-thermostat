"""Test the learning_thermostat integration."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test that the integration loads."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify runtime_data is populated
    assert mock_config_entry.runtime_data is not None
    assert mock_config_entry.runtime_data.data_collector is not None
    assert mock_config_entry.runtime_data.ml_core is not None
    assert isinstance(mock_config_entry.runtime_data.sensor_entities, list)

    assert hass.states.get("climate.learning_thermostat") is not None
