"""Regression tests for MLCore."""
import pytest
from unittest.mock import MagicMock
from custom_components.learning_thermostat.ml_core import MLCore
import pandas as pd
import numpy as np

@pytest.mark.asyncio
async def test_predict_temperature_attribute_error(hass):
    """Test that predict_temperature doesn't raise AttributeError for dayofweek."""
    ml_core = MLCore(hass, "dummy_data.csv", "dummy_model.joblib")

    # Mock the model and is_trained
    ml_core.model = MagicMock()
    ml_core.is_trained = True

    sensor_data = {"sensor_temp": 20.0}

    # This should not raise AttributeError
    prediction = await ml_core.async_predict_temperature(sensor_data)

    assert prediction is not None
