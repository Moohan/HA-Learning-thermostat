"""Config flow for Learning Thermostat."""
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def get_basic_schema(defaults: dict[str, Any] | None = None, include_advanced_toggle: bool = True) -> vol.Schema:
    """Return the basic schema."""
    if defaults is None:
        defaults = {}

    data_schema = {
        vol.Required(
            "target_climate_entity",
            default=defaults.get("target_climate_entity"),
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate"),
        ),
    }

    if defaults.get(CONF_NAME) is not None:
        data_schema[vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME))] = selector.TextSelector()
    else:
        data_schema[vol.Optional(CONF_NAME)] = selector.TextSelector()

    if include_advanced_toggle:
        data_schema[vol.Optional("advanced_options", default=False)] = selector.BooleanSelector()

    return vol.Schema(data_schema)

def get_advanced_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the advanced schema."""
    if defaults is None:
        defaults = {}
    return vol.Schema(
        {
            vol.Optional(
                "areas",
                default=defaults.get("areas", []),
            ): selector.AreaSelector(
                selector.AreaSelectorConfig(multiple=True),
            ),
            vol.Optional(
                "include_entities",
                default=defaults.get("include_entities", []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "binary_sensor"], multiple=True
                ),
            ),
            vol.Required(
                "override_duration",
                default=defaults.get("override_duration", 60),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=1440,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        }
    )

def get_options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the combined schema for the options flow (single-step)."""
    if defaults is None:
        defaults = {}

    basic_schema = get_basic_schema(defaults, include_advanced_toggle=False)
    advanced_schema = get_advanced_schema(defaults)

    # Merge underlying voluptuous schema mappings
    merged: dict[Any, Any] = {}
    merged.update(basic_schema.schema)
    merged.update(advanced_schema.schema)

    return vol.Schema(merged)


class LearningThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Learning Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.data.update(user_input)

            target = user_input["target_climate_entity"]
            await self.async_set_unique_id(f"learning_thermostat:{target}")
            self._abort_if_unique_id_configured()

            if user_input.get("advanced_options"):
                return await self.async_step_advanced()

            return self._create_entry()

        return self.async_show_form(
            step_id="user",
            data_schema=get_basic_schema(),
        )

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the advanced options step."""
        if user_input is not None:
            self.data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="advanced",
            data_schema=get_advanced_schema(self.data),
        )

    def _create_entry(self) -> FlowResult:
        """Create the config entry."""
        # Remove the internal 'advanced_options' flag
        self.data.pop("advanced_options", None)

        if not self.data.get(CONF_NAME):
            target_entity_id = self.data["target_climate_entity"]
            state = self.hass.states.get(target_entity_id)
            if state:
                self.data[CONF_NAME] = f"Learning {state.name}"
            else:
                self.data[CONF_NAME] = "Learning Thermostat"

        return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return LearningThermostatOptionsFlowHandler(config_entry)


class LearningThermostatOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Learning Thermostat."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry title if CONF_NAME has changed
            if CONF_NAME in user_input:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, title=user_input[CONF_NAME]
                )
            return self.async_create_entry(title="", data=user_input)

        # Merge data and options for the default values
        current_config = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=get_options_schema(current_config),
        )
