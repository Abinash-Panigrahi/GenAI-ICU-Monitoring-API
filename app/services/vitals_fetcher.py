import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from app.config import settings

async def fetch_patient_data(patient_mrn: str) -> dict:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=15)

    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.999Z")

    async with httpx.AsyncClient() as client:
        vital_signs, alarms = await asyncio.gather(
            client.get(
                f"{settings.hardware_api_url}/api/history/{patient_mrn}",
                params={"type": "vital_signs", "startDate": start_str, "endDate": end_str}
            ),
            client.get(
                f"{settings.hardware_api_url}/api/history/{patient_mrn}",
                params={"type": "alarms", "startDate": start_str, "endDate": end_str}
            )
        )

    vital_signs_data = vital_signs.json().get("data", {}).get("vital_signs", [])
    alarms_data = alarms.json().get("data", {}).get("alarms", [])

    filtered_vitals = []
    for record in vital_signs_data:
        for vital in record.get("vitals_json", []):
            if vital.get("value") != -1:
                filtered_vitals.append(vital)

    return {
        "patient_mrn": patient_mrn,
        "window_start": start_time,
        "window_end": end_time,
        "vital_signs": filtered_vitals,
        "alarms": alarms_data
    }