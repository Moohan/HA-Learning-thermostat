"""Config flow for Learning Thermostat."""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LearningThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Learning Thermostat."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step: selecting the target climate entity."""
        if user_input is not None:
            self.data["target_climate_entity"] = user_input["target_climate_entity"]
            return await self.async_step_areas()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("target_climate_entity"): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate"),
                    ),
                }
            ),
        )

    async def async_step_areas(self, user_input=None):
        """Handle the step for selecting areas and additional entities."""
        if user_input is not None:
            self.data["areas"] = user_input.get("areas", [])
            self.data["include_entities"] = user_input.get("include_entities", [])
            return await self.async_step_params()

        return self.async_show_form(
            step_id="areas",
            data_schema=vol.Schema(
                {
                    vol.Optional("areas"): selector.AreaSelector(
                        selector.AreaSelectorConfig(multiple=True),
                    ),
                    vol.Optional("include_entities"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "binary_sensor"], multiple=True
                        ),
                    ),
                }
            ),
        )

    async def async_step_params(self, user_input=None):
        """Handle the final step for setting parameters."""
        if user_input is not None:
            self.data.update(user_input)

            # Use the climate entity's friendly name as a default for the new component name
            if not self.data.get("name"):
                target_entity_id = self.data["target_climate_entity"]
                state = self.hass.states.get(target_entity_id)
                if state:
                    self.data["name"] = f"Learning {state.name}"
                else:
                    self.data["name"] = "Learning Thermostat"

            _LOGGER.info("Creating Learning Thermostat entry with data: %s", self.data)
            return self.async_create_entry(title=self.data["name"], data=self.data)

        return self.async_show_form(
            step_id="params",
            data_schema=vol.Schema(
                {
                    vol.Optional("name"): str,
                    vol.Required("override_duration", default=60): int,
                }
            ),
        )
