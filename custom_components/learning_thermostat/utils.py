"""Utility functions for the Learning Thermostat integration."""
from typing import Any
from homeassistant.config_entries import ConfigEntry

def sanitize_entity_id_for_feature(entity_id: str) -> str:
    """
    Sanitize an entity ID to be used as a feature name.
    Replaces '.' with '_' to avoid issues with data formats.
    """
    return entity_id.replace(".", "_")

def get_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Get the merged configuration from a config entry."""
    return {**entry.data, **entry.options}
