"""Machine Learning core for the Learning Thermostat integration."""
import logging
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from datetime import datetime

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class MLCore:
    """Manages the machine learning model."""

    def __init__(self, hass: HomeAssistant, data_path: str, model_path: str):
        """Initialize the ML core."""
        self.hass = hass
        self._data_path = data_path
        self._model_path = model_path
        self.model = None
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        """Load the trained model from a file."""
        if os.path.exists(self._model_path):
            try:
                self.model = joblib.load(self._model_path)
                self.is_trained = True
                _LOGGER.info("Successfully loaded pre-trained model.")
            except Exception as e:
                _LOGGER.error("Error loading model: %s", e)
        else:
            _LOGGER.info("No pre-trained model found. Waiting for training.")

    async def async_train_model(self):
        """Train the machine learning model from the collected data."""
        return await self.hass.async_add_executor_job(self._train_model_sync)

    def _train_model_sync(self):
        """Synchronous method to handle the CPU-bound training task."""
        _LOGGER.info("Starting model training...")

        if not os.path.exists(self._data_path):
            _LOGGER.warning("Data file not found. Cannot train model.")
            return False

        try:
            df = pd.read_csv(self._data_path)
        except Exception as e:
            _LOGGER.error("Error reading data file: %s", e)
            return False

        if len(df) < 20:
            _LOGGER.info("Not enough data to train. Have %d, need 20.", len(df))
            return False

        # --- Feature Engineering ---
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Cyclical time feature
        seconds_from_midnight = df['timestamp'].dt.hour * 3600 + df['timestamp'].dt.minute * 60 + df['timestamp'].dt.second
        seconds_in_day = 24 * 60 * 60
        df['time_sin'] = np.sin(2 * np.pi * seconds_from_midnight / seconds_in_day)
        df['time_cos'] = np.cos(2 * np.pi * seconds_from_midnight / seconds_in_day)
        
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df = df.drop('timestamp', axis=1)

        y = df['target_temperature']
        X = df.drop('target_temperature', axis=1)

        categorical_features = X.select_dtypes(include=['object', 'category']).columns
        numerical_features = X.select_dtypes(include=['number']).columns

        # --- Model Pipeline ---
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', 'passthrough', numerical_features),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ])

        self.model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
        ])

        self.model.fit(X, y)
        _LOGGER.info("Model training completed successfully.")

        try:
            joblib.dump(self.model, self._model_path)
            _LOGGER.info("Model saved to %s", self._model_path)
            self.is_trained = True
            return True
        except Exception as e:
            _LOGGER.error("Error saving model: %s", e)
            return False

    async def async_predict_temperature(self, sensor_data: dict):
        """Predict the target temperature based on current sensor data."""
        if not self.is_trained or self.model is None:
            _LOGGER.warning("Prediction requested, but model is not trained.")
            return None
        
        return await self.hass.async_add_executor_job(self._predict_temperature_sync, sensor_data)

    def _predict_temperature_sync(self, sensor_data: dict):
        """Synchronous method for CPU-bound prediction."""
        try:
            df = pd.DataFrame([sensor_data])
            
            # --- Feature Engineering (must match training) ---
            now = datetime.now()
            seconds_from_midnight = now.hour * 3600 + now.minute * 60 + now.second
            seconds_in_day = 24 * 60 * 60
            df['time_sin'] = np.sin(2 * np.pi * seconds_from_midnight / seconds_in_day)
            df['time_cos'] = np.cos(2 * np.pi * seconds_from_midnight / seconds_in_day)
            df['day_of_week'] = now.dayofweek

            prediction = self.model.predict(df)
            _LOGGER.info("Predicted temperature: %s", prediction[0])
            return prediction[0]
        except Exception as e:
            _LOGGER.error("Error during prediction: %s", e)
            return None
