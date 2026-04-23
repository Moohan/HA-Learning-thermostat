"""Extended tests for the Learning Thermostat climate platform."""
from unittest.mock import patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant, Context
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_TEMPERATURE,
    ATTR_MIN_TEMP,
    ATTR_MAX_TEMP,
    ATTR_TARGET_TEMP_STEP,
    HVACMode,
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


async def test_attribute_synchronization(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that attributes are synchronized from the target climate entity."""
    target_entity = "climate.test_climate"
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {
            ATTR_CURRENT_TEMPERATURE: 18.0,
            ATTR_MIN_TEMP: 15.0,
            ATTR_MAX_TEMP: 25.0,
            "target_temp_step": 0.1,
        },
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 18.0
    assert state.attributes.get(ATTR_MIN_TEMP) == 15.0
    assert state.attributes.get(ATTR_MAX_TEMP) == 25.0
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == 0.1

    # Update target entity attributes
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {
            ATTR_CURRENT_TEMPERATURE: 19.0,
            ATTR_MIN_TEMP: 16.0,
            ATTR_MAX_TEMP: 26.0,
            "target_temp_step": 0.2,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 19.0
    assert state.attributes.get(ATTR_MIN_TEMP) == 16.0
    assert state.attributes.get(ATTR_MAX_TEMP) == 26.0
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == 0.2


async def test_manual_override_detection(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that manual temperature changes on target entity trigger an override."""
    target_entity = "climate.test_climate"
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 20.0},
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Change temperature with user context
    user_context = Context(user_id="test_user")
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 22.0},
        context=user_context,
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_TEMPERATURE) == 22.0
    assert state.attributes.get("is_override_active") is True


async def test_ai_change_no_override(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that AI-driven temperature changes on target entity do NOT trigger an override."""
    target_entity = "climate.test_climate"
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 20.0},
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Change temperature WITHOUT user context (simulating AI or internal change)
    ai_context = Context() # No user_id
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 21.0},
        context=ai_context,
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    # Temperature should NOT be synced to _attr_target_temperature if it's not a manual override
    # in the current implementation, we ONLY sync _attr_target_temperature on manual override detection.
    # So it should remain at its previous value (default 21.0 in this case, coincidentally)
    # Wait, default is 21.0. Let's check.
    assert state.attributes.get("is_override_active") is False
