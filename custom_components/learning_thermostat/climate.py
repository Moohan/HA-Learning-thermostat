"""Climate platform for the Learning Thermostat integration."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback, Context
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)
from homeassistant.helpers.restore_state import RestoreEntity

from . import LearningThermostatConfigEntry
from .const import DOMAIN
from .utils import sanitize_entity_id_for_feature, get_entry_config

_LOGGER = logging.getLogger(__name__)

# Simplified HVAC modes
HVAC_MODES = [HVACMode.OFF, HVACMode.AUTO]
# Presets define the sub-mode of AUTO
PRESET_CONTROLLING = "Controlling"
PRESET_LEARNING_CONTROLLING = "Learning & Controlling"
PRESETS = [PRESET_CONTROLLING, PRESET_LEARNING_CONTROLLING]

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LearningThermostatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Learning Thermostat climate platform."""
    config = get_entry_config(entry)
    target_climate_entity = config["target_climate_entity"]
    override_duration = timedelta(minutes=config.get("override_duration", 60))
    temperature_unit = hass.config.units.temperature_unit

    async_add_entities(
        [
            LearningThermostat(
                entry,
                target_climate_entity,
                override_duration,
                temperature_unit,
            )
        ]
    )


class LearningThermostat(ClimateEntity, RestoreEntity):
    """Representation of a Learning Thermostat."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        entry: LearningThermostatConfigEntry,
        target_climate_entity: str,
        override_duration: timedelta,
        temperature_unit: str,
    ):
        """Initialize the thermostat."""
        self._entry = entry
        self._target_climate_entity = target_climate_entity
        self._sensor_entities = entry.runtime_data.sensor_entities
        self._data_collector = entry.runtime_data.data_collector
        self._ml_core = entry.runtime_data.ml_core
        self._override_duration = override_duration

        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Learning Thermostat",
            model="ML Thermostat",
        )

        self._attr_temperature_unit = temperature_unit
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_hvac_modes = HVAC_MODES

        if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            self._attr_target_temperature = 70.0
        else:
            self._attr_target_temperature = 21.0
        self._attr_current_temperature = None
        self._attr_hvac_mode = HVACMode.OFF  # Default to OFF
        self._attr_preset_mode = PRESET_LEARNING_CONTROLLING

        self._is_override_active = False
        self._override_end_time = None
        self._prediction_task = None
        self._state_listener = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_target_temperature = last_state.attributes.get(ATTR_TEMPERATURE, 21.0)
            if last_state.state:
                try:
                    hvac_mode = HVACMode(last_state.state)
                    if hvac_mode in HVAC_MODES:
                        self._attr_hvac_mode = hvac_mode
                    else:
                        self._attr_hvac_mode = HVACMode.OFF
                except ValueError:
                    self._attr_hvac_mode = HVACMode.OFF
            self._attr_preset_mode = last_state.attributes.get(
                "preset_mode", PRESET_LEARNING_CONTROLLING
            )

        self._state_listener = async_track_state_change_event(
            self.hass,
            [self._target_climate_entity],
            self._async_target_climate_state_listener,
        )

        target_state = self.hass.states.get(self._target_climate_entity)
        if target_state:
            self._update_target_state(target_state)

        await self._async_update_prediction_task()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed."""
        if self._prediction_task:
            self._prediction_task()
        if self._state_listener:
            self._state_listener()

    @callback
    def _update_target_state(self, state):
        """Update internal state from the target climate entity."""
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_current_temperature = state.attributes.get("current_temperature")
            self.async_write_ha_state()

    @callback
    def _async_target_climate_state_listener(self, event):
        """Handle state changes for the target climate entity."""
        self._update_target_state(event.data.get("new_state"))

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        return self._attr_preset_mode if self._attr_hvac_mode == HVACMode.AUTO else None

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return PRESETS if self._attr_hvac_mode == HVACMode.AUTO else None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "target_climate_entity": self._target_climate_entity,
            "model_trained": self._ml_core.is_trained,
            "is_override_active": self._is_override_active,
        }
        if self._is_override_active and self._override_end_time:
            attrs["override_ends_at"] = self._override_end_time.isoformat()
        return attrs

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature (manual override)."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._attr_target_temperature = temperature
        self._is_override_active = True
        self._override_end_time = dt_util.now() + self._override_duration

        _LOGGER.info(
            "%s: Manual override to %s°C until %s",
            self.name, temperature, self._override_end_time
        )

        await self._async_set_target_climate_temp(temperature, context=self._context)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        await self._async_update_prediction_task()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the thermostat on."""
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn the thermostat off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        if preset_mode not in PRESETS:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)
            return
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

    async def _async_update_prediction_task(self):
        """Start or stop the prediction task based on the current HVAC mode."""
        if self._prediction_task:
            self._prediction_task()
            self._prediction_task = None

        if self._attr_hvac_mode == HVACMode.AUTO:
            self._prediction_task = async_track_time_interval(
                self.hass, self._async_prediction_loop, SCAN_INTERVAL
            )

    async def _async_prediction_loop(self, now=None):
        """The main loop that gets predictions and sets the temperature."""
        if self._attr_hvac_mode != HVACMode.AUTO or not self._ml_core.is_trained:
            return

        if self._is_override_active:
            if dt_util.now() < self._override_end_time:
                return
            else:
                _LOGGER.info("%s: Manual override has ended.", self.name)
                self._is_override_active = False

        sensor_data = {}
        for entity_id in self._sensor_entities:
            state = self.hass.states.get(entity_id)
            feature_name = sanitize_entity_id_for_feature(entity_id)
            sensor_data[feature_name] = state.state if state else "unknown"

        predicted_temp = await self._ml_core.async_predict_temperature(sensor_data)

        if predicted_temp is not None:
            _LOGGER.info("%s: Predicted temperature: %s", self.name, predicted_temp)
            self._attr_target_temperature = round(predicted_temp, 1)
            await self._async_set_target_climate_temp(
                self._attr_target_temperature, context=Context()
            )
        else:
            _LOGGER.warning("%s: Failed to get a prediction.", self.name)
        
        self.async_write_ha_state()

    async def _async_set_target_climate_temp(self, temperature, context=None):
        """Set the temperature on the target climate entity."""
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": self._target_climate_entity, "temperature": temperature},
            blocking=True,
            context=context,
        )
