"""Tests for the MLCore of the Learning Thermostat integration."""
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from custom_components.learning_thermostat.ml_core import MLCore

async def test_predict_temperature_no_trained_model(hass):
    """Test prediction when no model is trained."""
    ml_core = MLCore(hass, "data.csv", "model.joblib")
    prediction = await ml_core.async_predict_temperature({"sensor1": 20})
    assert prediction is None

async def test_predict_temperature_attribute_error_fix(hass):
    """Test that prediction doesn't raise AttributeError (reproduction of fixed bug)."""
    ml_core = MLCore(hass, "data.csv", "model.joblib")

    # Mock a trained model
    ml_core.is_trained = True
    ml_core.model = MagicMock()
    ml_core.model.predict.return_value = np.array([22.5])

    # This should NOT raise AttributeError: 'datetime.datetime' object has no attribute 'dayofweek'
    prediction = await ml_core.async_predict_temperature({"sensor1": 20})

    assert prediction == 22.5
    ml_core.model.predict.assert_called_once()

async def test_train_model_not_enough_data(hass, tmp_path):
    """Test training with not enough data."""
    data_path = tmp_path / "data.csv"
    model_path = tmp_path / "model.joblib"

    # Create a CSV with only 5 rows
    df = pd.DataFrame({
        "timestamp": [pd.Timestamp.now()] * 5,
        "sensor1": [20] * 5,
        "target_temperature": [21] * 5
    })
    df.to_csv(data_path, index=False)

    ml_core = MLCore(hass, str(data_path), str(model_path))
    result = await ml_core.async_train_model()

    assert result is False
    assert ml_core.is_trained is False
