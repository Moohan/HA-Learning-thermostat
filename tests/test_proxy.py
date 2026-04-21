"""Tests for the proxy behavior of the Learning Thermostat."""
from unittest.mock import patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant, Context
from homeassistant.const import (
    ATTR_TEMPERATURE,
)
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_MIN_TEMP,
    ATTR_MAX_TEMP,
    ATTR_TARGET_TEMP_STEP,
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


async def test_proxy_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that attributes are proxied from the target entity."""
    target_entity_id = "climate.test_climate"
    hass.states.async_set(
        target_entity_id,
        "heat",
        {
            ATTR_CURRENT_TEMPERATURE: 22.5,
            ATTR_MIN_TEMP: 15.0,
            ATTR_MAX_TEMP: 25.0,
            ATTR_TARGET_TEMP_STEP: 0.5,
        },
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 22.5
    assert state.attributes[ATTR_MIN_TEMP] == 15.0
    assert state.attributes[ATTR_MAX_TEMP] == 25.0
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 0.5

    # Update target entity
    hass.states.async_set(
        target_entity_id,
        "heat",
        {
            ATTR_CURRENT_TEMPERATURE: 23.0,
            ATTR_MIN_TEMP: 16.0,
            ATTR_MAX_TEMP: 26.0,
            ATTR_TARGET_TEMP_STEP: 1.0,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 23.0
    assert state.attributes[ATTR_MIN_TEMP] == 16.0
    assert state.attributes[ATTR_MAX_TEMP] == 26.0
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 1.0


async def test_manual_override_from_target(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that manual changes on target entity trigger override."""
    target_entity_id = "climate.test_climate"
    hass.states.async_set(
        target_entity_id,
        "heat",
        {
            ATTR_TEMPERATURE: 20.0,
            ATTR_CURRENT_TEMPERATURE: 20.0,
        },
    )

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes["is_override_active"] is False

    # Simulate manual change on target entity (with user_id)
    context = Context(user_id="test_user")
    hass.states.async_set(
        target_entity_id,
        "heat",
        {
            ATTR_TEMPERATURE: 21.0,
            ATTR_CURRENT_TEMPERATURE: 20.0,
        },
        context=context,
    )
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state.attributes["is_override_active"] is True
    assert state.attributes[ATTR_TEMPERATURE] == 21.0
