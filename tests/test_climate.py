"""Tests for the Learning Thermostat climate platform."""
from unittest.mock import patch, AsyncMock
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
        yield mock_data_collector, mock_ml_core


async def test_climate_unique_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that the climate entity has the correct unique ID."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("climate.learning_thermostat")
    assert state is not None

    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get("climate.learning_thermostat")
    assert entity is not None
    assert entity.unique_id == mock_config_entry.entry_id


async def test_climate_unique_id_stability(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, patched_integration
) -> None:
    """Test that the climate entity unique ID remains stable after a rename."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get("climate.learning_thermostat")
    assert entity is not None
    original_unique_id = entity.unique_id
    assert original_unique_id == mock_config_entry.entry_id

    # Rename the entity in the registry
    entity_registry.async_update_entity(
        "climate.learning_thermostat", name="New Friendly Name"
    )
    await hass.async_block_till_done()

    # Verify unique_id is still the same
    entity = entity_registry.async_get("climate.learning_thermostat")
    assert entity.unique_id == original_unique_id
    assert entity.name == "New Friendly Name"

    # Change the config entry title (which might be used for default naming)
    hass.config_entries.async_update_entry(mock_config_entry, title="New Entry Title")
    await hass.async_block_till_done()

    # Verify unique_id is still the same
    entity = entity_registry.async_get("climate.learning_thermostat")
    assert entity.unique_id == original_unique_id
