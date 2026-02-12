"""Config flow for Learning Thermostat."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.const import CONF_NAME

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def get_basic_schema(defaults=None):
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

    if defaults.get(CONF_NAME):
        data_schema[vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME))] = selector.TextSelector()
    else:
        data_schema[vol.Optional(CONF_NAME)] = selector.TextSelector()

    data_schema[vol.Optional("advanced_options", default=False)] = selector.BooleanSelector()

    return vol.Schema(data_schema)

def get_advanced_schema(defaults=None):
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


class LearningThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Learning Thermostat."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            self.data.update(user_input)
            if user_input.get("advanced_options"):
                return await self.async_step_advanced()

            return self._create_entry()

        return self.async_show_form(
            step_id="user",
            data_schema=get_basic_schema(),
        )

    async def async_step_advanced(self, user_input=None):
        """Handle the advanced options step."""
        if user_input is not None:
            self.data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="advanced",
            data_schema=get_advanced_schema(self.data),
        )

    def _create_entry(self):
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
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return LearningThermostatOptionsFlowHandler(config_entry)


class LearningThermostatOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Learning Thermostat."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Merge data and options for the default values
        current_config = {**self.config_entry.data, **self.config_entry.options}

        full_schema = vol.Schema(
            {
                vol.Required(
                    "target_climate_entity",
                    default=current_config.get("target_climate_entity"),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate"),
                ),
                vol.Optional(
                    CONF_NAME,
                    default=current_config.get(CONF_NAME),
                ): selector.TextSelector(),
                vol.Optional(
                    "areas",
                    default=current_config.get("areas", []),
                ): selector.AreaSelector(
                    selector.AreaSelectorConfig(multiple=True),
                ),
                vol.Optional(
                    "include_entities",
                    default=current_config.get("include_entities", []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "binary_sensor"], multiple=True
                    ),
                ),
                vol.Required(
                    "override_duration",
                    default=current_config.get("override_duration", 60),
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

        return self.async_show_form(
            step_id="init",
            data_schema=full_schema,
        )
