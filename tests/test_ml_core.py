
import pytest
from unittest.mock import MagicMock
from custom_components.learning_thermostat.ml_core import MLCore
from homeassistant.core import HomeAssistant

@pytest.fixture
def ml_core(hass: HomeAssistant):
    return MLCore(hass, "test_data.csv", "test_model.joblib")

def test_predict_temperature_sync_fixed(ml_core):
    """Verify that the dayofweek bug is fixed."""
    ml_core.is_trained = True
    ml_core.model = MagicMock()
    ml_core.model.predict.return_value = [22.5]

    # This should no longer fail with AttributeError
    result = ml_core._predict_temperature_sync({"temp": 20})

    assert result == 22.5
    ml_core.model.predict.assert_called_once()
