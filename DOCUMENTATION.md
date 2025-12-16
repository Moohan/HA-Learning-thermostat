# Learning Thermostat Custom Component for Home Assistant

## 1. Project Vision & Goals

### 1.1. Overview

The goal of this project is to create a "smart" learning thermostat integration for Home Assistant. The system will operate by observing a user's manual interactions with a climate entity and correlating them with various environmental and temporal data points. After an initial learning phase, the integration will be able to predict and automate thermostat adjustments, optimizing for comfort and efficiency based on the learned patterns. The entire system will run locally within Home Assistant, ensuring user privacy.

### 1.2. Core Features

-   **Autonomous Learning:** Automatically learn user preferences from manual thermostat adjustments.
-   **Predictive Control:** Proactively adjust the target temperature based on learned patterns.
-   **Multi-Sensor Input:** Incorporate data from a wide range of sensors, including temperature, humidity, room presence, outdoor temperature, and time of day.
-   **User-Friendly Configuration:** A simple setup process within the Home Assistant UI, allowing users to select a target climate entity and associated areas.
-   **Operational Modes:** Provide distinct modes for `Learning`, `Controlling`, and `Learning & Controlling`.
-   **Manual Override:** Allow users to override the automation temporarily.
-   **Local Processing:** All data collection and model training will be handled locally on the user's Home Assistant instance.

---

## 2. Architecture

The custom component will be modular, consisting of three primary components: the **Data Collector**, the **Machine Learning (ML) Core**, and the **Controller Entity**.

### 2.1. Directory Structure

```
custom_components/learning_thermostat/
├── __init__.py         # Component setup and initialization
├── manifest.json       # Component metadata
├── const.py            # Constants used throughout the component
├── config_flow.py      # UI-based configuration handler
├── data_collector.py   # Service for collecting and storing sensor data
├── ml_core.py          # Machine learning model training and prediction
└── climate.py          # The main climate entity exposed to the user
```

### 2.2. Component Descriptions

#### 2.2.1. Data Collector (`data_collector.py`)

-   **Responsibility:** To gather and store time-series data from all relevant entities.
-   **Functionality:**
    -   Identifies and subscribes to state changes for the target `climate` entity and all sensors within user-selected `areas`.
    -   Listens for manual changes to the target `climate` entity's `temperature` attribute. Each manual change is treated as a target "label" for a training instance.
    -   When a manual change is detected, it captures the state of all monitored sensors at that moment.
    -   Stores this data point (features + target temperature) in a simple, local format (e.g., a CSV file or a SQLite database).

#### 2.2.2. Machine Learning Core (`ml_core.py`)

-   **Responsibility:** To manage the lifecycle of the machine learning model.
-   **Functionality:**
    -   **Model Choice:** Will use a lightweight, efficient regression model from the `scikit-learn` library, suitable for running on a Raspberry Pi 5 (e.g., `RandomForestRegressor` or `GradientBoostingRegressor`).
    -   **Training:**
        -   Loads the historical data collected by the `Data Collector`.
        -   Performs feature engineering (e.g., encoding cyclical features like time of day).
        -   Trains the regression model to predict `target_temperature`.
        -   Saves the trained model object to a file (`.joblib` or `.pkl`).
    -   **Prediction:**
        -   Loads the saved model.
        -   Accepts the current state of all sensors as input.
        -   Returns a predicted target temperature.
    -   **Retraining:** A service will be exposed to trigger model retraining on-demand or on a schedule.

#### 2.2.3. Controller Entity (`climate.py`)

-   **Responsibility:** To provide the user-facing interface and control logic.
-   **Functionality:**
    -   Creates a new `climate` entity (e.g., `climate.learning_thermostat`).
    -   **State & Attributes:**
        -   Displays the current predicted target temperature.
        -   Exposes an `input_select` or similar control to switch between operational modes (`Learning`, `Controlling`, etc.).
        -   Reports the current status (e.g., "Model is training," "Controlling," "Manual Override Active").
    -   **Control Logic:**
        -   In `Controlling` mode, it periodically calls the `ML Core` for a prediction and then calls the `climate.set_temperature` service on the *target* climate entity.
        -   Handles manual overrides on its own temperature setting. When a user changes its target temperature, it will pause predictions for a configurable duration and pass the change through to the target climate entity.

---

## 3. Data Model

### 3.1. Feature Set

The model will be trained on the following features (and more, as discovered from the area):

-   `time_of_day_sin`, `time_of_day_cos`: Time of day, encoded as cyclical features.
-   `day_of_week`: Day of the week (0-6).
-   `outdoor_temperature`: From an external sensor.
-   `current_temperature_room_X`: Current temperature for a given room.
-   `current_humidity_room_X`: Current humidity for a given room (optional).
-   `presence_room_X`: Occupancy status for a given room (binary or count).
-   `house_occupancy`: Overall house occupancy state.

### 3.2. Target Variable

-   `target_temperature`: The temperature value set manually by the user on the original `climate` entity.

### 3.3. Data Storage

-   A CSV file (`learning_thermostat_data.csv`) will be stored in the Home Assistant `config` directory. Each row will represent a single training instance (a manual adjustment). This keeps the data portable and easy for users to inspect.

---

## 4. Configuration Flow (`config_flow.py`)

The setup process will be handled via the UI.

1.  **Step 1: Select Target Climate Entity:**
    -   The user is presented with a dropdown of all `climate` entities in their system.
2.  **Step 2: Select Areas & Entities:**
    -   The user is shown a checklist of all `areas` in their Home Assistant instance.
    -   They can select the areas that contain relevant sensors. The integration will automatically find and subscribe to all relevant sensors within those areas.
    -   An additional entity picker will allow them to add specific sensors from outside the selected areas (e.g., an outdoor temperature sensor).
3.  **Step 3: Set Parameters:**
    -   **Override Duration:** A number input for how long a manual override should last (e.g., 60 minutes).
    -   **Component Name:** A text input for the name of the created climate entity.

---

## 5. User Guide

### 5.1. Installation

-   Instructions on how to install the custom component (e.g., via HACS or manually).

### 5.2. Setup

-   A walkthrough of the configuration flow.

### 5.3. How It Works

-   **Learning Mode:** Explain that in this mode, the user should interact with their *original* thermostat as they normally would. The learning thermostat will silently collect data in the background.
-   **Controlling Mode:** Once enough data is collected, the user can switch to this mode. The `climate.learning_thermostat` entity will now control the original thermostat. The user should interact with the *new* learning entity from this point on.
-   **Manual Overrides:** Explain how to manually set a temperature and how the system will resume automatic control after the override period expires.
