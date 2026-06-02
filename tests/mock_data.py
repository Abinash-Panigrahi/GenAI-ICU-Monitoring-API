# tests/mock_data.py

MOCK_PATIENTS = {
    "CRASH_TEST": {
        "Respiratory": [
            {"parameter": "SpO2", "unit": "%", "status": "connected", "first_value": 98, "latest_value": 82, "average_value": 89, "trend": "DECREASING", "velocity_per_min": -1.06, "time_below_threshold_sec": 120, "disconnected_readings": 0, "disconnection_periods": []},
            {"parameter": "RR", "unit": "rpm", "status": "connected", "first_value": 16, "latest_value": 34, "average_value": 26, "trend": "INCREASING", "velocity_per_min": 1.2, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []}
        ],
        "Cardiovascular": [
            {"parameter": "HR", "unit": "bpm", "status": "connected", "first_value": 85, "latest_value": 145, "average_value": 115, "trend": "INCREASING", "velocity_per_min": 4.0, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []},
            {"parameter": "NIBP-S", "unit": "mmHg", "status": "connected", "first_value": 115, "latest_value": 85, "average_value": 95, "trend": "DECREASING", "velocity_per_min": -2.0, "time_below_threshold_sec": 60, "disconnected_readings": 0, "disconnection_periods": []}
        ],
        "Neurological": [
            {"parameter": "GCS-Total", "unit": "", "status": "connected", "first_value": 15, "latest_value": 11, "average_value": 13, "trend": "DECREASING", "velocity_per_min": -0.2, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []}
        ],
        "Other": []
    },
    
    "SEPSIS_TEST": {
        "Respiratory": [
            {"parameter": "RR", "unit": "rpm", "status": "connected", "first_value": 20, "latest_value": 28, "average_value": 24, "trend": "INCREASING", "velocity_per_min": 0.53, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []}
        ],
        "Cardiovascular": [
            {"parameter": "HR", "unit": "bpm", "status": "connected", "first_value": 90, "latest_value": 118, "average_value": 105, "trend": "INCREASING", "velocity_per_min": 1.86, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []},
            {"parameter": "NIBP-S", "unit": "mmHg", "status": "sensor_disconnected", "first_value": 0, "latest_value": 0, "average_value": 0, "trend": "STABLE", "velocity_per_min": 0, "time_below_threshold_sec": 0, "disconnected_readings": 180, "disconnection_periods": [{"start": "ongoing", "end": "ongoing"}]}
        ],
        "Neurological": [
            {"parameter": "GCS-Total", "unit": "", "status": "connected", "first_value": 15, "latest_value": 14, "average_value": 14, "trend": "DECREASING", "velocity_per_min": -0.06, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []}
        ],
        "Other": [
            {"parameter": "T1", "unit": "C", "status": "connected", "first_value": 37.5, "latest_value": 39.2, "average_value": 38.5, "trend": "INCREASING", "velocity_per_min": 0.11, "time_below_threshold_sec": 0, "disconnected_readings": 0, "disconnection_periods": []}
        ]
    }
}