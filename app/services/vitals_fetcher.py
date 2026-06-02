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


def summarize_vitals(vital_signs_data: list) -> dict:
    # 1. Add this map to group parameters by organ system
    organ_map = {
        "SpO2": "Respiratory",
        "RR": "Respiratory",
        "HR": "Cardiovascular",
        "PR": "Cardiovascular",
        "PI": "Cardiovascular",
        "NIBP-S": "Cardiovascular",
        "NIBP-D": "Cardiovascular",
        "NIBP-M": "Cardiovascular",
        "GCS-Total": "Neurological",
        "GCS-Eye": "Neurological",
        "GCS-Motor": "Neurological",
        "GCS-Verbal": "Neurological"
    }

    # 2. Change the summary from a flat list [] to a categorized dictionary
    summary = {
        "Respiratory": [],
        "Cardiovascular": [],
        "Neurological": [],
        "Other": []
    }
    
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


    for param_name, param_data in grouped.items():
        readings = param_data["readings"]
        unit = param_data["unit"]

        valid = [r for r in readings if r["value"] != -1]
        invalid = [r for r in readings if r["value"] == -1]

        disconnected_count = len(invalid)
        connected_count = len(valid)

        # 3. Match the parameter to its organ system
        system_category = organ_map.get(param_name, "Other")

        # 4. Track Exact Disconnection Start & End Times
        disconnection_periods = []
        if disconnected_count > 0:
            is_disconnected = False
            start_time = None
            for r in readings:
                if r["value"] == -1 and not is_disconnected:
                    start_time = r["time"]
                    is_disconnected = True
                elif r["value"] != -1 and is_disconnected:
                    disconnection_periods.append({"start": start_time, "end": r["time"]})
                    is_disconnected = False
            if is_disconnected:
                disconnection_periods.append({"start": start_time, "end": "ongoing"})

        if connected_count == 0:
            summary[system_category].append({
                "parameter": param_name,
                "status": "sensor_disconnected",
                "disconnected_readings": disconnected_count,
                "disconnection_periods": disconnection_periods,
                "valid_readings": 0
            })
        else:
            values = [r["value"] for r in valid]
            first_value = values[0]
            latest_value = values[-1]
            average_value = round(sum(values) / len(values), 2)

            # 5. Velocity: (Difference between latest and first) / 15 minutes
            velocity_per_min = round((latest_value - first_value) / 15, 2)

            if latest_value > first_value * 1.05:
                trend = "INCREASING"
            elif latest_value < first_value * 0.95:
                trend = "DECREASING"
            else:
                trend = "STABLE"

            # 6. Time-in-Range: Count bad readings and multiply by 5 seconds
            time_below_threshold_sec = 0
            if param_name == "SpO2":
                time_below_threshold_sec = len([v for v in values if v < 90]) * 5
            elif param_name == "NIBP-S":
                time_below_threshold_sec = len([v for v in values if v < 90]) * 5

            # Save the final block into the correct organ system list
            summary[system_category].append({
                "parameter": param_name,
                "unit": unit,
                "status": "connected",
                "valid_readings": connected_count,
                "first_value": first_value,
                "latest_value": latest_value,
                "average_value": average_value,
                "trend": trend,
                "velocity_per_min": velocity_per_min,
                "time_below_threshold_sec": time_below_threshold_sec,
                "disconnected_readings": disconnected_count,
                "disconnection_periods": disconnection_periods
            })

    return summary