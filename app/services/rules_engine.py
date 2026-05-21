# ── Single parameter thresholds ──────────────────────────────────────────────
VITAL_THRESHOLDS = {
    "HR":     {"min": 40,  "max": 150, "unit": "bpm"},
    "SpO2":   {"min": 90,  "max": 100, "unit": "%"},
    "RR":     {"min": 8,   "max": 30,  "unit": "rpm"},
    "NIBP-S": {"min": 90,  "max": 180, "unit": "mmHg"},
    "NIBP-D": {"min": 40,  "max": 110, "unit": "mmHg"},
    "NIBP-M": {"min": 65,  "max": 120, "unit": "mmHg"},
    "T1":     {"min": 35,  "max": 39,  "unit": "C"},
    "T2":     {"min": 35,  "max": 39,  "unit": "C"},
    "PR":     {"min": 40,  "max": 150, "unit": "bpm"},
}


def get_latest(vital_signs: list, param: str):
    for v in vital_signs:
        if v.get("parameter") == param:
            return v.get("latest_value")
    return None


def get_trend(vital_signs: list, param: str):
    for v in vital_signs:
        if v.get("parameter") == param:
            return v.get("trend")
    return None


def get_status(vital_signs: list, param: str):
    for v in vital_signs:
        if v.get("parameter") == param:
            return v.get("status")
    return None


def check_single_parameters(vital_signs: list) -> list:
    anomalies = []

    for vital in vital_signs:
        param = vital.get("parameter")
        status = vital.get("status")
        latest = vital.get("latest_value")
        trend = vital.get("trend")
        unit = vital.get("unit", "")
        disconnected_count = vital.get("disconnected_readings", 0)
        reconnected_at = vital.get("reconnected_at")

        # sensor disconnected entire window
        if status == "sensor_disconnected":
            anomalies.append({
                "parameter": param,
                "issue": "sensor disconnected entire window",
                "severity": "warning",
                "type": "sensor"
            })
            continue

        # sensor was disconnected but reconnected
        if disconnected_count > 0 and reconnected_at:
            anomalies.append({
                "parameter": param,
                "issue": f"sensor was disconnected, reconnected at {reconnected_at}",
                "severity": "info",
                "type": "sensor"
            })

        # threshold checks
        if param in VITAL_THRESHOLDS and latest is not None:
            limits = VITAL_THRESHOLDS[param]

            if latest < limits["min"]:
                anomalies.append({
                    "parameter": param,
                    "value": latest,
                    "unit": unit,
                    "issue": f"below minimum ({limits['min']} {limits['unit']})",
                    "trend": trend,
                    "severity": "critical",
                    "type": "threshold"
                })

            elif latest > limits["max"]:
                anomalies.append({
                    "parameter": param,
                    "value": latest,
                    "unit": unit,
                    "issue": f"above maximum ({limits['max']} {limits['unit']})",
                    "trend": trend,
                    "severity": "warning",
                    "type": "threshold"
                })

        # dangerous trends
        if trend == "INCREASING" and param in ["HR", "RR"]:
            anomalies.append({
                "parameter": param,
                "issue": f"{param} trending INCREASING — monitor closely",
                "severity": "warning",
                "type": "trend"
            })

        if trend == "DECREASING" and param in ["SpO2", "NIBP-S", "NIBP-M"]:
            anomalies.append({
                "parameter": param,
                "issue": f"{param} trending DECREASING — monitor closely",
                "severity": "warning",
                "type": "trend"
            })

    return anomalies


def check_combinations(vital_signs: list) -> list:
    combination_alerts = []

    hr     = get_latest(vital_signs, "HR")
    sbp    = get_latest(vital_signs, "NIBP-S")
    dbp    = get_latest(vital_signs, "NIBP-D")
    map_   = get_latest(vital_signs, "NIBP-M")
    spo2   = get_latest(vital_signs, "SpO2")
    rr     = get_latest(vital_signs, "RR")
    temp   = get_latest(vital_signs, "T1") or get_latest(vital_signs, "T2")
    pr     = get_latest(vital_signs, "PR")

    sbp_trend = get_trend(vital_signs, "NIBP-S")
    hr_trend  = get_trend(vital_signs, "HR")

    # ── 1. SHOCK ─────────────────────────────────────────────────────────────
    if hr and sbp and hr > 110 and sbp < 90:
        combination_alerts.append({
            "name": "SHOCK",
            "severity": "critical",
            "parameters": f"HR={hr}bpm, SBP={sbp}mmHg",
            "note": "Tachycardia with hypotension indicating possible shock state."
        })

    # ── Shock Index ───────────────────────────────────────────────────────────
    if hr and sbp and sbp > 0:
        shock_index = round(hr / sbp, 2)
        if shock_index > 0.9:
            combination_alerts.append({
                "name": "SHOCK INDEX ELEVATED",
                "severity": "warning",
                "parameters": f"Shock Index={shock_index} (HR={hr}/SBP={sbp})",
                "note": f"Shock Index {shock_index} > 0.9 — early indicator of shock even before BP drops."
            })

    # ── 2. RESPIRATORY DISTRESS ───────────────────────────────────────────────
    if rr and spo2 and rr > 30 and spo2 < 90:
        combination_alerts.append({
            "name": "RESPIRATORY DISTRESS",
            "severity": "critical",
            "parameters": f"RR={rr}rpm, SpO2={spo2}%",
            "note": "Increased respiratory effort with hypoxia — acute respiratory failure."
        })

    # ── 3. SEPSIS ─────────────────────────────────────────────────────────────
    if temp and hr and rr and temp > 38 and hr > 100 and rr > 24:
        combination_alerts.append({
            "name": "SEPSIS SUSPECTED",
            "severity": "critical",
            "parameters": f"Temp={temp}C, HR={hr}bpm, RR={rr}rpm",
            "note": "Vitals suggest systemic infection with risk of sepsis (SIRS criteria met)."
        })

    # ── 4. CARDIAC INSTABILITY ────────────────────────────────────────────────
    if hr and sbp and (hr > 150 or hr < 40) and sbp < 90:
        combination_alerts.append({
            "name": "CARDIAC INSTABILITY",
            "severity": "critical",
            "parameters": f"HR={hr}bpm, SBP={sbp}mmHg",
            "note": "Extreme heart rate with low BP — possible arrhythmia with hemodynamic collapse."
        })

    # ── 5. PRE-ARREST ─────────────────────────────────────────────────────────
    if hr and sbp and hr < 40 and sbp < 70:
        combination_alerts.append({
            "name": "PRE-ARREST",
            "severity": "critical",
            "parameters": f"HR={hr}bpm, SBP={sbp}mmHg",
            "note": "Severe hemodynamic collapse — pre-arrest condition. Immediate intervention required."
        })

    # ── 6. PERFUSION FAILURE ──────────────────────────────────────────────────
    if map_ and sbp and map_ < 65 and sbp < 90:
        combination_alerts.append({
            "name": "PERFUSION FAILURE",
            "severity": "critical",
            "parameters": f"MAP={map_}mmHg, SBP={sbp}mmHg",
            "note": "MAP below 65 with hypotension — inadequate organ perfusion."
        })

    # ── 7. SEPSIS / SYSTEMIC FAILURE (lighter version) ───────────────────────
    if hr and rr and hr > 100 and rr > 24 and not temp:
        combination_alerts.append({
            "name": "SYSTEMIC STRESS",
            "severity": "warning",
            "parameters": f"HR={hr}bpm, RR={rr}rpm",
            "note": "Tachycardia with elevated respiratory rate — possible systemic stress or early sepsis."
        })

    return combination_alerts


def calculate_risk_score(anomalies: list, combination_alerts: list) -> dict:
    score = 0

    # points from combinations
    for alert in combination_alerts:
        if alert["severity"] == "critical":
            score += 30
        elif alert["severity"] == "warning":
            score += 15

    # points from single parameter anomalies
    for anomaly in anomalies:
        if anomaly["severity"] == "critical":
            score += 15
        elif anomaly["severity"] == "warning":
            score += 8
        elif anomaly["severity"] == "info":
            score += 2

    # cap at 100
    score = min(score, 100)

    if score <= 30:
        risk_level = "Stable"
    elif score <= 60:
        risk_level = "Moderate"
    elif score <= 80:
        risk_level = "High Risk"
    else:
        risk_level = "Critical"

    return {
        "risk_score": score,
        "risk_level": risk_level
    }


def analyze_vitals(vital_signs: list, alarms: list) -> dict:

    # step 1 — single parameter checks
    anomalies = check_single_parameters(vital_signs)

    # step 2 — combination checks
    combination_alerts = check_combinations(vital_signs)

    # step 3 — alarm checks
    for alarm in alarms:
        anomalies.append({
            "parameter": alarm.get("alarm_type"),
            "issue": alarm.get("alarm_text"),
            "severity": "warning",
            "type": "alarm"
        })

    # step 4 — overall severity
    severity = "normal"
    if any(a["severity"] == "critical" for a in anomalies):
        severity = "critical"
    elif any(a["severity"] == "warning" for a in anomalies):
        severity = "warning"
    if any(c["severity"] == "critical" for c in combination_alerts):
        severity = "critical"
    elif any(c["severity"] == "warning" for c in combination_alerts) and severity == "normal":
        severity = "warning"

    # step 5 — risk score
    risk = calculate_risk_score(anomalies, combination_alerts)

    return {
        "anomalies": anomalies,
        "combination_alerts": combination_alerts,
        "severity": severity,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"]
    }