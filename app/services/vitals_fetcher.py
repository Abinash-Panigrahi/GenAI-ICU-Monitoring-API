import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from app.config import settings

async def fetch_patient_data(patient_mrn: str) -> dict:

    if settings.use_test_date:
        start_time = datetime.fromisoformat(settings.test_start_date.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(settings.test_end_date.replace("Z", "+00:00"))
        print(f"🗓️ Using test dates: {start_time} → {end_time}")
    else:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)
        print(f"🗓️ Using live dates: {start_time} → {end_time}")

    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.999Z")

    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"⏳ Fetching data for {patient_mrn}...")
        vital_signs, alarms = await asyncio.gather(
            client.get(
                f"{settings.hardware_api_url}/api/vitals/{patient_mrn}/history",
                params={"type": "vitals", "startDate": start_str, "endDate": end_str}
            ),
            client.get(
                f"{settings.hardware_api_url}/api/vitals/{patient_mrn}/history",
                params={"type": "alarms", "startDate": start_str, "endDate": end_str}
            )
        )
        print(f"✅ Data fetched successfully!")
        print(f"📊 Vital signs records: {len(vital_signs.json().get('data', {}).get('vitals', []))}")
        print(f"🚨 Alarms records: {len(alarms.json().get('data', {}).get('alarms', []))}")

    vital_signs_data = vital_signs.json().get("data", {}).get("vitals", [])
    alarms_data = alarms.json().get("data", {}).get("alarms", [])
    alarms_data = alarms_data[-20:]

    summarized_vitals = summarize_vitals(vital_signs_data)

    return {
        "patient_mrn": patient_mrn,
        "window_start": start_time,
        "window_end": end_time,
        "vital_signs": summarized_vitals,
        "alarms": alarms_data
    }


def summarize_vitals(vital_signs_data: list) -> list:
    grouped = {}

    for record in vital_signs_data:
        for vital in record.get("vitals_json", []):
            name = vital.get("parameterName")
            value = vital.get("value")
            obs_time = vital.get("observationTime", "")

            if "1969" in obs_time:
                continue

            if name not in grouped:
                grouped[name] = {
                    "unit": vital.get("unit", ""),
                    "readings": []
                }

            grouped[name]["readings"].append({
                "value": value,
                "time": obs_time
            })

    summary = []

    for param_name, param_data in grouped.items():
        readings = param_data["readings"]
        unit = param_data["unit"]

        valid = [r for r in readings if r["value"] != -1]
        invalid = [r for r in readings if r["value"] == -1]

        disconnected_count = len(invalid)
        connected_count = len(valid)

        if connected_count == 0:
            summary.append({
                "parameter": param_name,
                "unit": unit,
                "status": "sensor_disconnected",
                "disconnected_readings": disconnected_count,
                "valid_readings": 0,
                "first_value": None,
                "latest_value": None,
                "average_value": None,
                "trend": None,
                "reconnected_at": None
            })
        else:
            values = [r["value"] for r in valid]
            first_value = values[0]
            latest_value = values[-1]
            average_value = round(sum(values) / len(values), 2)

            if len(values) >= 2:
                if latest_value > first_value * 1.05:
                    trend = "INCREASING"
                elif latest_value < first_value * 0.95:
                    trend = "DECREASING"
                else:
                    trend = "STABLE"
            else:
                trend = "STABLE"

            reconnected_at = None
            if disconnected_count > 0:
                for r in readings:
                    if r["value"] != -1:
                        reconnected_at = r["time"]
                        break

            summary.append({
                "parameter": param_name,
                "unit": unit,
                "status": "connected",
                "disconnected_readings": disconnected_count,
                "valid_readings": connected_count,
                "first_value": first_value,
                "latest_value": latest_value,
                "average_value": average_value,
                "trend": trend,
                "reconnected_at": reconnected_at
            })

    return summary