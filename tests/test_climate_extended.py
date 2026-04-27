"""Extended tests for the Learning Thermostat climate platform."""
from unittest.mock import patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant, Context
from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ATTR_MIN_TEMP,
    ATTR_MAX_TEMP,
    ATTR_TARGET_TEMP_STEP,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID
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
        mock_data_collector_inst = mock_data_collector.return_value
        mock_data_collector_inst.async_setup = AsyncMock()
        mock_data_collector_inst.learning_enabled = True

        mock_ml_core_inst = mock_ml_core.return_value
        mock_ml_core_inst.async_initialize = AsyncMock()
        mock_ml_core_inst.async_train_model = AsyncMock()
        mock_ml_core_inst.is_trained = False
        yield mock_data_collector_inst, mock_ml_core_inst


async def test_attribute_synchronization(
    hass: HomeAssistant, patched_integration
) -> None:
    """Test that min_temp, max_temp, and target_temp_step are synchronized."""
    target_entity_id = "climate.target"
    hass.states.async_set(
        target_entity_id,
        HVACMode.HEAT,
        {
            ATTR_MIN_TEMP: 15.0,
            ATTR_MAX_TEMP: 25.0,
            ATTR_TARGET_TEMP_STEP: 0.1,
            "current_temperature": 20.0,
            ATTR_TEMPERATURE: 21.0,
        },
    )

    mock_config_entry = MockConfigEntry(
        domain="learning_thermostat",
        data={
            "target_climate_entity": target_entity_id,
            "areas": [],
            "include_entities": [],
            "name": "Learning Thermostat",
            "override_duration": 60,
        },
        title="Learning Thermostat",
        unique_id="mock_unique_id",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_MIN_TEMP) == 15.0
    assert state.attributes.get(ATTR_MAX_TEMP) == 25.0
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == 0.1
    assert state.attributes.get("current_temperature") == 20.0

    # Update target entity attributes and verify sync
    hass.states.async_set(
        target_entity_id,
        HVACMode.HEAT,
        {
            ATTR_MIN_TEMP: 10.0,
            ATTR_MAX_TEMP: 30.0,
            ATTR_TARGET_TEMP_STEP: 1.0,
            "current_temperature": 22.0,
            ATTR_TEMPERATURE: 21.0,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get(ATTR_MIN_TEMP) == 10.0
    assert state.attributes.get(ATTR_MAX_TEMP) == 30.0
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == 1.0
    assert state.attributes.get("current_temperature") == 22.0


async def test_manual_override_detection(
    hass: HomeAssistant, patched_integration
) -> None:
    """Test that manual changes on the target entity activate override."""
    target_entity_id = "climate.target"
    hass.states.async_set(target_entity_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 20.0})

    mock_config_entry = MockConfigEntry(
        domain="learning_thermostat",
        data={
            "target_climate_entity": target_entity_id,
            "areas": [],
            "include_entities": [],
            "name": "Learning Thermostat",
            "override_duration": 60,
        },
        title="Learning Thermostat",
        unique_id="mock_unique_id",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Simulate manual change by user on target entity
    hass.states.async_set(
        target_entity_id,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 22.0},
        context=Context(user_id="user_123"),
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("is_override_active") is True
    assert state.attributes.get(ATTR_TEMPERATURE) == 22.0


async def test_preset_mode_learning_toggle(
    hass: HomeAssistant, patched_integration
) -> None:
    """Test that switching presets toggles learning_enabled in DataCollector."""
    mock_data_collector, _ = patched_integration
    target_entity_id = "climate.target"
    hass.states.async_set(target_entity_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 20.0})

    mock_config_entry = MockConfigEntry(
        domain="learning_thermostat",
        data={
            "target_climate_entity": target_entity_id,
            "areas": [],
            "include_entities": [],
            "name": "Learning Thermostat",
            "override_duration": 60,
        },
        title="Learning Thermostat",
        unique_id="mock_unique_id",
    )
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Turn on to AUTO so preset_modes is available
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {ATTR_ENTITY_ID: "climate.learning_thermostat", "hvac_mode": HVACMode.AUTO},
        blocking=True,
    )

    # Default is Learning & Controlling
    assert mock_data_collector.learning_enabled is True

    # Switch to Controlling only
    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {ATTR_ENTITY_ID: "climate.learning_thermostat", "preset_mode": PRESET_CONTROLLING},
        blocking=True,
    )
    assert mock_data_collector.learning_enabled is False

    # Switch back to Learning & Controlling
    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {ATTR_ENTITY_ID: "climate.learning_thermostat", "preset_mode": PRESET_LEARNING_CONTROLLING},
        blocking=True,
    )
    assert mock_data_collector.learning_enabled is True
