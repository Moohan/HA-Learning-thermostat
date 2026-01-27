"""Fixtures for the Learning Thermostat integration tests."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.learning_thermostat.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "target_climate_entity": "climate.test_climate",
            "areas": [],
            "include_entities": [],
            "name": "Learning Thermostat",
            "override_duration": 60,
        },
        title="Learning Thermostat",
        unique_id="learning_thermostat",
    )
