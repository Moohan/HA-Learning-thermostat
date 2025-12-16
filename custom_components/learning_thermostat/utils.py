"""Utility functions for the Learning Thermostat integration."""


def sanitize_entity_id_for_feature(entity_id: str) -> str:
    """
    Sanitize an entity ID to be used as a feature name.
    Replaces '.' with '_' to avoid issues with data formats.
    """
    return entity_id.replace(".", "_")
