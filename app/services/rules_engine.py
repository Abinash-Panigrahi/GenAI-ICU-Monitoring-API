from typing import dict

VITAL_THRESHOLDS = {
    "HR": {"min": 40, "max": 150, "unit": "bpm"},
    "SpO2": {"min": 90, "max": 100, "unit": "%"},
    "RR": {"min": 8, "max": 30, "unit": "rpm"},
    "NIBP-S": {"min": 70, "max": 180, "unit": "mmHg"},
    "NIBP-D": {"min": 40, "max": 110, "unit": "mmHg"},
    "T1": {"min": 35, "max": 39, "unit": "C"},
    "T2": {"min": 35, "max": 39, "unit": "C"},
}

def analyze_vitals(vital_signs: list, alarms: list) -> dict:
    anomalies = []
    severity = "normal"

    for vital in vital_signs:
        name = vital.get("parameterName")
        value = vital.get("value")
        unit = vital.get("unit")

        if name in VITAL_THRESHOLDS:
            limits = VITAL_THRESHOLDS[name]

            if value < limits["min"]:
                anomalies.append({
                    "parameter": name,
                    "value": value,
                    "unit": unit,
                    "issue": f"below minimum ({limits['min']} {limits['unit']})",
                    "severity": "critical"
                })
                severity = "critical"

            elif value > limits["max"]:
                anomalies.append({
                    "parameter": name,
                    "value": value,
                    "unit": unit,
                    "issue": f"above maximum ({limits['max']} {limits['unit']})",
                    "severity": "warning"
                })
                if severity != "critical":
                    severity = "warning"

    for alarm in alarms:
        anomalies.append({
            "parameter": alarm.get("alarm_type"),
            "issue": alarm.get("alarm_text"),
            "severity": "warning"
        })
        if severity == "normal":
            severity = "warning"

    return {
        "anomalies": anomalies,
        "severity": severity
    }