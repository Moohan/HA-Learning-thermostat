"""Extended tests for the Learning Thermostat climate platform."""
from unittest.mock import patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def patched_integration():
    """Fixture to patch DataCollector and MLCore."""
    with patch(
        "custom_components.learning_thermostat.DataCollector"
    ) as mock_data_collector, patch(
        "custom_components.learning_thermostat.MLCore"
    ) as mock_ml_core:
        mock_data_collector.return_value.async_setup = AsyncMock()
        mock_ml_core.return_value.async_initialize = AsyncMock()
        mock_ml_core.return_value.async_train_model = AsyncMock()
        mock_ml_core.return_value.is_trained = False
        yield


async def test_climate_attribute_sync(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that the climate entity synchronizes attributes from the target entity."""
    target_entity_id = "climate.test_climate"

    # Set initial state for target climate
    hass.states.async_set(
        target_entity_id,
        HVACMode.HEAT,
        {
            ATTR_CURRENT_TEMPERATURE: 20.0,
            ATTR_TEMPERATURE: 21.0,
            "min_temp": 15.0,
            "max_temp": 25.0,
            "target_temp_step": 0.1,
        },
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state is not None
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 20.0
    assert state.attributes.get("min_temp") == 15.0
    assert state.attributes.get("max_temp") == 25.0
    assert state.attributes.get("target_temp_step") == 0.1

    # Update target state
    hass.states.async_set(
        target_entity_id,
        HVACMode.HEAT,
        {
            ATTR_CURRENT_TEMPERATURE: 19.0,
            ATTR_TEMPERATURE: 21.0,
            "min_temp": 10.0,
            "max_temp": 30.0,
            "target_temp_step": 1.0,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 19.0
    assert state.attributes.get("min_temp") == 10.0
    assert state.attributes.get("max_temp") == 30.0
    assert state.attributes.get("target_temp_step") == 1.0
