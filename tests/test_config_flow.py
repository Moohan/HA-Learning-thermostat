"""Test the Learning Thermostat config flow."""
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from custom_components.learning_thermostat.const import DOMAIN

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

async def test_config_flow_simple_path(hass: HomeAssistant) -> None:
    """Test the simple config flow path."""
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
    # It should have generated a name if not provided
    assert result["data"]["target_climate_entity"] == "climate.living_room"
    assert "name" in result["data"]

async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="My Thermostat",
        data={
            "target_climate_entity": "climate.living_room",
            "name": "My Thermostat",
            "override_duration": 60,
        },
        entry_id="test_entry",
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "target_climate_entity": "climate.bedroom",
            "name": "New Name",
            "override_duration": 120,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["target_climate_entity"] == "climate.bedroom"
    assert result["data"]["name"] == "New Name"
    assert result["data"]["override_duration"] == 120
