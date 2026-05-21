VITAL_THRESHOLDS = {
    "HR": {"min": 40, "max": 150, "unit": "bpm"},
    "SpO2": {"min": 90, "max": 100, "unit": "%"},
    "RR": {"min": 8, "max": 30, "unit": "rpm"},
    "NIBP-S": {"min": 70, "max": 180, "unit": "mmHg"},
    "NIBP-D": {"min": 40, "max": 110, "unit": "mmHg"},
    "T1": {"min": 35, "max": 39, "unit": "C"},
    "T2": {"min": 35, "max": 39, "unit": "C"},
    "PR": {"min": 40, "max": 150, "unit": "bpm"},
}

def analyze_vitals(vital_signs: list, alarms: list) -> dict:
    anomalies = []
    severity = "normal"

    for vital in vital_signs:
        param = vital.get("parameter")
        status = vital.get("status")
        latest = vital.get("latest_value")
        trend = vital.get("trend")
        unit = vital.get("unit", "")
        reconnected_at = vital.get("reconnected_at")
        disconnected_count = vital.get("disconnected_readings", 0)

        # check if sensor was disconnected
        if status == "sensor_disconnected":
            anomalies.append({
                "parameter": param,
                "issue": "sensor disconnected entire window",
                "severity": "warning"
            })
            if severity == "normal":
                severity = "warning"
            continue

        # check if sensor was disconnected but reconnected
        if disconnected_count > 0 and reconnected_at:
            anomalies.append({
                "parameter": param,
                "issue": f"sensor was disconnected, reconnected at {reconnected_at}",
                "severity": "info"
            })

        # check thresholds
        if param in VITAL_THRESHOLDS and latest is not None:
            limits = VITAL_THRESHOLDS[param]

            if latest < limits["min"]:
                anomalies.append({
                    "parameter": param,
                    "value": latest,
                    "unit": unit,
                    "issue": f"below minimum ({limits['min']} {limits['unit']})",
                    "trend": trend,
                    "severity": "critical"
                })
                severity = "critical"

            elif latest > limits["max"]:
                anomalies.append({
                    "parameter": param,
                    "value": latest,
                    "unit": unit,
                    "issue": f"above maximum ({limits['max']} {limits['unit']})",
                    "trend": trend,
                    "severity": "warning"
                })
                if severity != "critical":
                    severity = "warning"

        # check dangerous trends
        if trend == "INCREASING" and param in ["HR", "RR"]:
            anomalies.append({
                "parameter": param,
                "issue": f"trending INCREASING — monitor closely",
                "severity": "warning"
            })
            if severity == "normal":
                severity = "warning"

        if trend == "DECREASING" and param in ["SpO2"]:
            anomalies.append({
                "parameter": param,
                "issue": f"SpO2 trending DECREASING — monitor closely",
                "severity": "warning"
            })
            if severity == "normal":
                severity = "warning"

    # check alarms
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