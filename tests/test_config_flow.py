"""Test the Learning Thermostat config flow."""
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from custom_components.learning_thermostat.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_config_flow_full_path(hass: HomeAssistant) -> None:
    """Test the full config flow path including advanced options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # Fill basic options and check advanced
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "target_climate_entity": "climate.living_room",
            "name": "My Thermostat",
            "advanced_options": True,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "advanced"

    # Fill advanced options
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "areas": ["living_room"],
            "include_entities": ["sensor.outside_temp"],
            "override_duration": 30,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Thermostat"
    assert result["data"]["target_climate_entity"] == "climate.living_room"
    assert result["data"]["name"] == "My Thermostat"
    assert result["data"]["areas"] == ["living_room"]
    assert result["data"]["include_entities"] == ["sensor.outside_temp"]
    assert result["data"]["override_duration"] == 30

    # Ensure internal flag is not persisted to the config entry data
    assert "advanced_options" not in result["data"]

async def test_config_flow_simple_path_with_existing_entity(hass: HomeAssistant) -> None:
    """Test the simple config flow path when the target entity exists."""
    hass.states.async_set(
        "climate.living_room",
        "heat",
        {"friendly_name": "Living Room"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Fill basic options WITHOUT advanced
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "target_climate_entity": "climate.living_room",
            "advanced_options": False,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Learning Living Room"
    assert result["data"]["target_climate_entity"] == "climate.living_room"
    assert result["data"]["name"] == "Learning Living Room"

async def test_config_flow_simple_path_without_entity(hass: HomeAssistant) -> None:
    """Test the simple config flow path when the target entity does not exist."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Fill basic options WITHOUT advanced
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "target_climate_entity": "climate.living_room",
            "advanced_options": False,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Learning Thermostat"
    assert result["data"]["target_climate_entity"] == "climate.living_room"
    assert result["data"]["name"] == "Learning Thermostat"

async def test_config_flow_duplicate_abort(hass: HomeAssistant) -> None:
    """Test that the config flow aborts if the climate entity is already configured."""
    # Setup an existing entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"target_climate_entity": "climate.living_room"},
        unique_id="learning_thermostat:climate.living_room",
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Try to configure the same entity
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "target_climate_entity": "climate.living_room",
            "advanced_options": False,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"

async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow and merging of data/options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="My Thermostat",
        data={
            "target_climate_entity": "climate.living_room",
            "name": "My Thermostat",
            "override_duration": 60,
            "areas": ["living_room"],
            "include_entities": ["sensor.living_room_temperature"],
        },
        options={
            # Options should override data where both provide a value
            "target_climate_entity": "climate.bedroom",
            "override_duration": 90,
        },
        entry_id="test_entry",
    )
    config_entry.add_to_hass(hass)

    # Start the options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    # The form defaults should reflect the merged data/options
    data_schema = result["data_schema"].schema

    # Extract keys from the schema to check defaults
    def get_default(schema_dict, key_name):
        for key in schema_dict:
            if key == key_name or (hasattr(key, "schema") and key.schema == key_name):
                from voluptuous import Undefined
                default = key.default
                if default is Undefined:
                    return None
                if callable(default):
                    return default()
                return default
        return None

    assert get_default(data_schema, "target_climate_entity") == "climate.bedroom"
    assert get_default(data_schema, "override_duration") == 90
    assert get_default(data_schema, "name") == "My Thermostat"
    assert get_default(data_schema, "areas") == ["living_room"]
    assert get_default(data_schema, "include_entities") == ["sensor.living_room_temperature"]

    # Submit the form with a new name and ensure title is updated
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "target_climate_entity": "climate.bedroom",
            "name": "New Name",
            "override_duration": 120,
            "areas": ["living_room"],
            "include_entities": ["sensor.living_room_temperature"],
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "target_climate_entity": "climate.bedroom",
        "name": "New Name",
        "override_duration": 120,
        "areas": ["living_room"],
        "include_entities": ["sensor.living_room_temperature"],
    }

    # Verify the config entry title was updated
    assert config_entry.title == "New Name"
