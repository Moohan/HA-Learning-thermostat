
from unittest.mock import MagicMock
from custom_components.learning_thermostat.ml_core import MLCore
from homeassistant.core import HomeAssistant

def test_predict_temperature_dayofweek_bug(hass: HomeAssistant):
    """Test that prediction doesn't fail due to dayofweek AttributeError."""
    ml_core = MLCore(hass, "fake_data.csv", "fake_model.joblib")

    # Mock the model and is_trained
    ml_core.model = MagicMock()
    ml_core.is_trained = True

    sensor_data = {"sensor_temp": "20.5"}

    # This should not raise AttributeError, but currently it might be caught by try-except in _predict_temperature_sync
    # We want to ensure it doesn't log an error or return None due to AttributeError
    # But wait, _predict_temperature_sync has a try-except that catches everything and returns None.

    prediction = ml_core._predict_temperature_sync(sensor_data)

    # If the bug exists, prediction will be None because of the exception caught in the try-except block
    # and we should see an error in the logs.
    # Actually, we can just check if it returns None (assuming the mock model would return something if called)

    ml_core.model.predict.return_value = [22.0]

    prediction = ml_core._predict_temperature_sync(sensor_data)

    assert prediction == 22.0
