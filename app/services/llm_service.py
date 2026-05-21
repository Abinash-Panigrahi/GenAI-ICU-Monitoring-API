from google import genai
import json
import time
from app.config import settings

client = genai.Client(api_key=settings.llm_api_key)

PROMPT_VERSION = "v1.0"
MODEL = "gemini-2.5-flash"

def build_prompt(patient_mrn: str, vital_signs: list, alarms: list, anomalies: list) -> str:

    vitals_text = ""
    for vital in vital_signs:
        param = vital.get("parameter")
        unit = vital.get("unit", "")
        status = vital.get("status")

        if status == "sensor_disconnected":
            vitals_text += f"- {param}: SENSOR DISCONNECTED entire window\n"
        else:
            first = vital.get("first_value")
            latest = vital.get("latest_value")
            avg = vital.get("average_value")
            trend = vital.get("trend")
            disconnected = vital.get("disconnected_readings", 0)
            reconnected_at = vital.get("reconnected_at")

            line = f"- {param}: first={first}{unit}, latest={latest}{unit}, avg={avg}{unit}, trend={trend}"

            if disconnected > 0 and reconnected_at:
                line += f" (was disconnected, reconnected at {reconnected_at})"

            vitals_text += line + "\n"

    alarms_text = ""
    if alarms:
        for alarm in alarms:
            alarms_text += f"- {alarm.get('alarm_text')} ({alarm.get('alarm_type')})\n"
    else:
        alarms_text = "No active alarms"

    anomalies_text = ""
    if anomalies:
        for anomaly in anomalies:
            anomalies_text += f"- {anomaly.get('parameter')}: {anomaly.get('issue')} [{anomaly.get('severity')}]\n"
    else:
        anomalies_text = "No anomalies detected"

    return f"""You are a clinical monitoring assistant helping ICU doctors and nurses.
Analyze the following patient data from the last monitoring window and write a short clinical report.

Patient MRN: {patient_mrn}

VITALS SUMMARY (first → latest value, with trend):
{vitals_text}

ACTIVE ALARMS:
{alarms_text}

DETECTED ANOMALIES:
{anomalies_text}

Reply ONLY with this JSON — no extra text, no markdown:
{{
    "summary": "2-3 sentences about overall patient status in this window",
    "concerns": "specific concerns needing attention, or None if stable",
    "trend_assessment": "are things getting better, worse, or stable overall?"
}}

Rules:
- Do NOT suggest medications or treatments
- Keep it short and clinical
- Mention sensor disconnections if relevant
- Focus on trends not just latest values"""


async def generate_report(
    patient_mrn: str,
    vital_signs: list,
    alarms: list,
    anomalies: dict
) -> dict:

    prompt = build_prompt(
        patient_mrn,
        vital_signs,
        alarms,
        anomalies.get("anomalies", [])
    )

    start = time.time()

    try:
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        latency = round(time.time() - start, 2)

        # clean the response text
        response_text = response.text.strip()

        # remove markdown code blocks if Gemini adds them
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        result = json.loads(response_text)

        return {
            "summary": result.get("summary", "Unable to generate summary"),
            "concerns": result.get("concerns", "None"),
            "trend_assessment": result.get("trend_assessment", "Unable to assess"),
            "model_used": MODEL,
            "prompt_version": PROMPT_VERSION,
            "llm_latency_seconds": latency
        }

    except json.JSONDecodeError:
        # if JSON parsing fails return a safe fallback
        return {
            "summary": "Report generation failed — AI response was not in expected format",
            "concerns": "Manual review required",
            "trend_assessment": "Unable to assess",
            "model_used": MODEL,
            "prompt_version": PROMPT_VERSION,
            "llm_latency_seconds": round(time.time() - start, 2)
        }

    except Exception as e:
        # if anything else fails
        return {
            "summary": f"Report generation failed — {str(e)}",
            "concerns": "Manual review required",
            "trend_assessment": "Unable to assess",
            "model_used": MODEL,
            "prompt_version": PROMPT_VERSION,
            "llm_latency_seconds": round(time.time() - start, 2)
        }