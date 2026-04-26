"""Extended tests for the Learning Thermostat climate platform."""
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import timedelta
import pytest

from homeassistant.core import HomeAssistant, Context
from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ATTR_CURRENT_TEMPERATURE,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, UnitOfTemperature
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed


@pytest.fixture
def mock_data_collector():
    """Mock DataCollector."""
    with patch("custom_components.learning_thermostat.DataCollector") as mock:
        collector = mock.return_value
        collector.async_setup = AsyncMock()
        collector.stop = MagicMock()
        collector.learning_enabled = True
        yield collector


@pytest.fixture
def mock_ml_core():
    """Mock MLCore."""
    with patch("custom_components.learning_thermostat.MLCore") as mock:
        ml = mock.return_value
        ml.async_initialize = AsyncMock()
        ml.async_train_model = AsyncMock()
        ml.is_trained = False
        yield ml


async def test_climate_proxy_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_data_collector,
    mock_ml_core,
) -> None:
    """Test that attributes are proxied from the target entity."""
    mock_config_entry.add_to_hass(hass)

    # Pre-set target entity state
    target_entity = mock_config_entry.data["target_climate_entity"]
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {
            ATTR_TEMPERATURE: 22.0,
            ATTR_CURRENT_TEMPERATURE: 21.0,
            "min_temp": 15.0,
            "max_temp": 25.0,
            "target_temp_step": 0.1,
        },
    )

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("min_temp") == 15.0
    assert state.attributes.get("max_temp") == 25.0
    assert state.attributes.get("target_temp_step") == 0.1
    assert state.attributes.get(ATTR_TEMPERATURE) == 22.0
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 21.0

    # Update target entity
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {
            ATTR_TEMPERATURE: 23.0,
            ATTR_CURRENT_TEMPERATURE: 22.5,
            "min_temp": 16.0,
            "max_temp": 26.0,
            "target_temp_step": 0.2,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("min_temp") == 16.0
    assert state.attributes.get("max_temp") == 26.0
    assert state.attributes.get("target_temp_step") == 0.2
    assert state.attributes.get(ATTR_TEMPERATURE) == 23.0
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 22.5


async def test_manual_override_from_target(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_data_collector,
    mock_ml_core,
) -> None:
    """Test that manual changes on the target entity trigger an override."""
    mock_config_entry.add_to_hass(hass)
    target_entity = mock_config_entry.data["target_climate_entity"]
    hass.states.async_set(target_entity, HVACMode.HEAT, {ATTR_TEMPERATURE: 20.0})

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Change temperature on target with a user_id
    hass.states.async_set(
        target_entity,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE: 22.0},
        context=Context(user_id="test_user"),
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes.get("is_override_active") is True
    assert state.attributes.get(ATTR_TEMPERATURE) == 22.0


async def test_preset_mode_toggles_learning(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_data_collector,
    mock_ml_core,
) -> None:
    """Test that changing preset mode toggles learning_enabled on DataCollector."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Initial state (Learning & Controlling)
    assert mock_data_collector.learning_enabled is True

    # Need to turn ON (set to AUTO) to have presets available
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {ATTR_ENTITY_ID: "climate.learning_thermostat", "hvac_mode": HVACMode.AUTO},
        blocking=True,
    )

    # Change to Controlling
    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {ATTR_ENTITY_ID: "climate.learning_thermostat", "preset_mode": "Controlling"},
        blocking=True,
    )
    assert mock_data_collector.learning_enabled is False

    # Change back to Learning & Controlling
    await hass.services.async_call(
        "climate",
        "set_preset_mode",
        {
            ATTR_ENTITY_ID: "climate.learning_thermostat",
            "preset_mode": "Learning & Controlling",
        },
        blocking=True,
    )
    assert mock_data_collector.learning_enabled is True
