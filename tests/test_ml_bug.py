
import pytest
from custom_components.learning_thermostat.ml_core import MLCore
import pandas as pd

@pytest.mark.asyncio
async def test_predict_temperature_bug(hass, tmp_path):
    data_path = str(tmp_path / "data.csv")
    model_path = str(tmp_path / "model.joblib")

    # Create a dummy CSV with enough data
    df = pd.DataFrame({
        "timestamp": [pd.Timestamp.now()] * 20,
        "sensor_1": [20.0] * 20,
        "target_temperature": [22.0] * 20
    })
    df.to_csv(data_path, index=False)

    ml_core = MLCore(hass, data_path, model_path)

    # Train the model
    await ml_core.async_train_model()
    assert ml_core.is_trained

    # This should trigger the bug
    prediction = await ml_core.async_predict_temperature({"sensor_1": 20.0})
    assert prediction is not None
