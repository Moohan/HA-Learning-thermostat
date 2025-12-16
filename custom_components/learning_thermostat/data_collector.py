"""Data collector for the Learning Thermostat integration."""

import logging
import os
import csv
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import ATTR_TEMPERATURE

from .utils import sanitize_entity_id_for_feature

_LOGGER = logging.getLogger(__name__)


class DataCollector:
    """Manages the collection of training data."""

    def __init__(
        self,
        hass: HomeAssistant,
        climate_entity_id: str,
        sensor_entity_ids: list[str],
        storage_path: str,
    ):
        """Initialize the data collector."""
        self.hass = hass
        self._climate_entity_id = climate_entity_id
        self._sensor_entity_ids = sensor_entity_ids
        self._storage_path = storage_path

        self._feature_names = [
            sanitize_entity_id_for_feature(eid) for eid in self._sensor_entity_ids
        ]
        self._fieldnames = ["timestamp"] + self._feature_names + ["target_temperature"]
        self._unsubscribe = None

    async def async_setup(self):
        """Set up the data collector and listeners."""
        _LOGGER.info("Setting up Data Collector for %s", self._climate_entity_id)

        self._init_csv_file()

        self._unsubscribe = async_track_state_change_event(
            self.hass,
            [self._climate_entity_id],
            self._async_handle_initial_learning_state_change,
        )

    def _init_csv_file(self):
        """Initialize the CSV file with a header if it doesn't exist."""
        if not os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, mode="w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self._fieldnames)
                    writer.writeheader()
            except IOError as e:
                _LOGGER.error("Error initializing CSV file: %s", e)

    @callback
    def _async_handle_initial_learning_state_change(self, event):
        """Handle state changes for the target climate entity during the initial learning phase."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if old_state is None or new_state is None:
            return

        old_temp = old_state.attributes.get(ATTR_TEMPERATURE)
        new_temp = new_state.attributes.get(ATTR_TEMPERATURE)

        if old_temp != new_temp and new_temp is not None:
            _LOGGER.info(
                "Initial learning: Target temp for %s changed to %s. Collecting data.",
                self._climate_entity_id,
                new_temp,
            )
            self.hass.async_create_task(self.async_collect_data_point(new_temp))

    async def async_collect_data_point(self, target_temperature):
        """Public method to collect and store a single data point from all sensors."""
        data_row = {"timestamp": datetime.now().isoformat()}

        for i, entity_id in enumerate(self._sensor_entity_ids):
            state = self.hass.states.get(entity_id)
            feature_name = self._feature_names[i]
            data_row[feature_name] = state.state if state else "unknown"

        data_row["target_temperature"] = target_temperature

        await self.hass.async_add_executor_job(self._write_to_csv, data_row)

    def _write_to_csv(self, data_row):
        """Write a row of data to the CSV file."""
        try:
            with open(self._storage_path, mode="a", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self._fieldnames)
                writer.writerow(data_row)
        except IOError as e:
            _LOGGER.error("Error writing to CSV file: %s", e)
        except Exception as e:
            _LOGGER.error("An unexpected error occurred while writing to CSV: %s", e)

    def stop(self):
        """Stop the data collector."""
        if self._unsubscribe:
            self._unsubscribe()
