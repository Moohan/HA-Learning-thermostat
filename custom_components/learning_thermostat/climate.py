"""Climate platform for the Learning Thermostat integration."""
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .data_collector import DataCollector
from .ml_core import MLCore
from .utils import sanitize_entity_id_for_feature

_LOGGER = logging.getLogger(__name__)

# Simplified HVAC modes
HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_AUTO]
# Presets define the sub-mode of AUTO
PRESET_CONTROLLING = "Controlling"
PRESET_LEARNING_CONTROLLING = "Learning & Controlling"
PRESETS = [PRESET_CONTROLLING, PRESET_LEARNING_CONTROLLING]

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Learning Thermostat climate platform."""
    data_collector = hass.data[DOMAIN][entry.entry_id]["data_collector"]
    ml_core = hass.data[DOMAIN][entry.entry_id]["ml_core"]
    sensor_entities = hass.data[DOMAIN][entry.entry_id]["sensor_entities"]

    config = entry.data
    name = config.get("name", "Learning Thermostat")
    target_climate_entity = config["target_climate_entity"]
    override_duration = timedelta(minutes=config.get("override_duration", 60))

    async_add_entities(
        [
            LearningThermostat(
                hass,
                name,
                target_climate_entity,
                sensor_entities,
                data_collector,
                ml_core,
                override_duration,
            )
        ]
    )


class LearningThermostat(ClimateEntity, RestoreEntity):
    """Representation of a Learning Thermostat."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        target_climate_entity: str,
        sensor_entities: list[str],
        data_collector: DataCollector,
        ml_core: MLCore,
        override_duration: timedelta,
    ):
        """Initialize the thermostat."""
        self.hass = hass
        self._name = name
        self._target_climate_entity = target_climate_entity
        self._sensor_entities = sensor_entities
        self._data_collector = data_collector
        self._ml_core = ml_core
        self._override_duration = override_duration

        self._target_temperature = 21.0
        self._current_temperature = None
        self._hvac_mode = HVAC_MODE_OFF  # Default to OFF
        self._preset_mode = PRESET_LEARNING_CONTROLLING

        self._is_override_active = False
        self._override_end_time = None
        self._prediction_task = None
        self._state_listener = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state:
            self._target_temperature = last_state.attributes.get(ATTR_TEMPERATURE, 21.0)
            self._hvac_mode = last_state.state or HVAC_MODE_OFF
            self._preset_mode = last_state.attributes.get(
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
            self._current_temperature = state.attributes.get("current_temperature")
            self.async_write_ha_state()

    @callback
    def _async_target_climate_state_listener(self, event):
        """Handle state changes for the target climate entity."""
        self._update_target_state(event.data.get("new_state"))

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"learning_thermostat_{self._name.lower().replace(' ', '_')}"

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
        
    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return HVAC_MODES

    @property
    def preset_mode(self):
        return self._preset_mode if self._hvac_mode == HVAC_MODE_AUTO else None

    @property
    def preset_modes(self):
        return PRESETS if self._hvac_mode == HVAC_MODE_AUTO else None

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def current_temperature(self):
        return self._current_temperature

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

        self._target_temperature = temperature
        self._is_override_active = True
        self._override_end_time = datetime.now() + self._override_duration

        _LOGGER.info(
            "%s: Manual override to %s°C until %s",
            self.name, temperature, self._override_end_time
        )

        # Continuous Learning: record this manual adjustment
        if self._preset_mode == PRESET_LEARNING_CONTROLLING:
            _LOGGER.info("Recording manual override as new learning data point.")
            await self._data_collector.async_collect_data_point(temperature)

        await self._async_set_target_climate_temp(temperature)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._hvac_mode = hvac_mode
        await self._async_update_prediction_task()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        if preset_mode not in PRESETS:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)
            return
        self._preset_mode = preset_mode
        self.async_write_ha_state()

    async def _async_update_prediction_task(self):
        """Start or stop the prediction task based on the current HVAC mode."""
        if self._prediction_task:
            self._prediction_task()
            self._prediction_task = None

        if self._hvac_mode == HVAC_MODE_AUTO:
            self._prediction_task = async_track_time_interval(
                self.hass, self._async_prediction_loop, SCAN_INTERVAL
            )

    async def _async_prediction_loop(self, now=None):
        """The main loop that gets predictions and sets the temperature."""
        if self._hvac_mode != HVAC_MODE_AUTO or not self._ml_core.is_trained:
            return

        if self._is_override_active:
            if datetime.now() < self._override_end_time:
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
            self._target_temperature = round(predicted_temp, 1)
            await self._async_set_target_climate_temp(self._target_temperature)
        else:
            _LOGGER.warning("%s: Failed to get a prediction.", self.name)
        
        self.async_write_ha_state()

    async def _async_set_target_climate_temp(self, temperature):
        """Set the temperature on the target climate entity."""
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": self._target_climate_entity, "temperature": temperature},
            blocking=True,
        )
