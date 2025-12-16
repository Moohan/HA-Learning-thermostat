# Learning Thermostat for Home Assistant

This is a custom component for Home Assistant that creates a "smart" learning thermostat. The system observes your manual interactions with a climate entity and learns your preferences to automate thermostat adjustments, optimizing for comfort and efficiency.

## Installation

### HACS

1.  Go to HACS -> Integrations -> ... (top right) -> Custom Repositories
2.  Enter `https://github.com/Moohan/HA-Learning-thermostat` as the repository and `Integration` as the category.
3.  Click "Add".
4.  The "Learning Thermostat" integration will now be available to install in HACS.

### Manual Installation

1.  Copy the `custom_components/learning_thermostat` directory to your Home Assistant `custom_components` directory.
2.  Restart Home Assistant.
3.  The "Learning Thermostat" integration will now be available to add in the integrations page.
