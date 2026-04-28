"""Extended tests for the Learning Thermostat climate platform."""
from unittest.mock import patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant, Context
from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ATTR_CURRENT_TEMPERATURE,
    HVACMode,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.learning_thermostat.climate import (
    PRESET_CONTROLLING,
    PRESET_LEARNING_CONTROLLING,
)

@pytest.fixture
def patched_integration():
    """Fixture to patch DataCollector and MLCore."""
    with patch(
        "custom_components.learning_thermostat.DataCollector", autospec=True
    ) as mock_data_collector, patch(
        "custom_components.learning_thermostat.MLCore", autospec=True
    ) as mock_ml_core:
        mock_data_collector.return_value.async_setup = AsyncMock()
        mock_ml_core.return_value.async_initialize = AsyncMock()
        mock_ml_core.return_value.async_train_model = AsyncMock()
        mock_ml_core.return_value.is_trained = False
        yield mock_data_collector, mock_ml_core

async def test_attribute_synchronization(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that attributes are synchronized from the target climate entity."""
    # Initial state of target entity
    hass.states.async_set(
        "climate.test_climate",
        HVACMode.HEAT,
        {
            ATTR_CURRENT_TEMPERATURE: 20.0,
            "min_temp": 15.0,
            "max_temp": 25.0,
            "target_temp_step": 1.0,
        },
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 20.0
    assert state.attributes.get("min_temp") == 15.0
    assert state.attributes.get("max_temp") == 25.0
    assert state.attributes.get("target_temp_step") == 1.0

async def test_manual_change_on_target_triggers_override(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that a manual temperature change on the target entity triggers an override."""
    # Ensure target entity exists
    hass.states.async_set(
        "climate.test_climate",
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 20.0},
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Set it to AUTO to ensure preset modes are active
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.learning_thermostat", "hvac_mode": HVACMode.AUTO},
        blocking=True,
    )

    old_state = hass.states.get("climate.test_climate")
    new_state_attrs = {ATTR_TEMPERATURE: 22.0}
    hass.states.async_set(
        "climate.test_climate",
        HVACMode.HEAT,
        new_state_attrs,
    )
    new_state = hass.states.get("climate.test_climate")

    # Simulate a manual change by a user (context.user_id is set)
    context = Context(user_id="test_user")

    # Fire event directly since mock_state_change_event is limited
    hass.bus.async_fire(
        "state_changed",
        {
            "entity_id": "climate.test_climate",
            "old_state": old_state,
            "new_state": new_state,
        },
        context=context,
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("is_override_active") is True
    assert state.attributes.get(ATTR_TEMPERATURE) == 22.0

async def test_learning_toggle_via_presets(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that learning is enabled/disabled when changing presets."""
    mock_data_collector, _ = patched_integration

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Set it to AUTO to ensure preset modes are active
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.learning_thermostat", "hvac_mode": HVACMode.AUTO},
        blocking=True,
    )

    # Default preset is Learning & Controlling
    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("preset_mode") == PRESET_LEARNING_CONTROLLING

    # Check that learning_enabled was set on the data collector instance
    data_collector_instance = mock_data_collector.return_value
    assert data_collector_instance.learning_enabled is True

    # Change to Controlling (Learning disabled)
    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {"entity_id": "climate.learning_thermostat", "preset_mode": PRESET_CONTROLLING},
        blocking=True,
    )

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("preset_mode") == PRESET_CONTROLLING
    assert data_collector_instance.learning_enabled is False

    # Change back to Learning & Controlling
    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {"entity_id": "climate.learning_thermostat", "preset_mode": PRESET_LEARNING_CONTROLLING},
        blocking=True,
    )
    assert data_collector_instance.learning_enabled is True
