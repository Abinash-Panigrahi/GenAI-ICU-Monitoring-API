from google import genai
from google.genai import types
import json
import time
from app.config import settings

client = genai.Client(api_key=settings.llm_api_key)

PROMPT_VERSION = "v1.0"
MODEL = "gemini-2.5-flash"

def build_prompt(patient_mrn: str, vital_signs: dict, alarms: list, anomalies: list, combination_alerts: list, risk_score: int, risk_level: str, mews_score: int, qsofa_score: int) -> str:

    vitals_text = ""
    # Loop through the new grouped dictionary
    for system, params in vital_signs.items():
        if not params: continue
        vitals_text += f"\n--- {system.upper()} ---\n"
        for vital in params:
            param = vital.get("parameter")
            unit = vital.get("unit", "")
            status = vital.get("status")

            if status == "sensor_disconnected":
                vitals_text += f"- {param}: SENSOR DISCONNECTED entire window\n"
            else:
                latest = vital.get("latest_value")
                avg = vital.get("average_value")
                trend = vital.get("trend")
                velocity = vital.get("velocity_per_min", 0)
                time_below = vital.get("time_below_threshold_sec", 0)
                
                line = f"- {param}: {latest}{unit} (Avg: {avg}{unit}, Trend: {trend}, Velocity: {velocity}/min)"
                
                if time_below > 0:
                    line += f" [⚠️ TIME-IN-RANGE ALERT: Spent {time_below} seconds below safe threshold!]"
                
                disconnected = vital.get("disconnected_readings", 0)
                if disconnected > 0:
                    line += f" (Sensor disconnected {disconnected} times)"
                vitals_text += line + "\n"

    alarms_text = ""
    if alarms:
        for alarm in alarms:
            alarms_text += f"- {alarm.get('alarm_text')} ({alarm.get('alarm_type')})\n"
    else:
        alarms_text = "No active alarms"

    anomalies_text = ""
    if anomalies:
        for anomaly in anomalies[:15]:
            anomalies_text += f"- {anomaly.get('parameter')}: {anomaly.get('issue')} [{anomaly.get('severity')}]\n"
    else:
        anomalies_text = "No anomalies detected"

    combinations_text = ""
    if combination_alerts:
        for combo in combination_alerts:
            combinations_text += f"- {combo['name']} [{combo['severity'].upper()}]: {combo['note']} (Parameters: {combo['parameters']})\n"
    else:
        combinations_text = "No combination alerts detected"

    return f"""You are an expert ICU attending physician analyzing 15-minute window telemetry data.
Write a highly concise, doctor-grade clinical summary.

Patient MRN: {patient_mrn}
Risk Score: {risk_score}/100 — {risk_level}
MEWS Score: {mews_score}
qSOFA Score: {qsofa_score}

ORGAN SYSTEM TELEMETRY (with Time-in-Range and Velocity):
{vitals_text}

ACTIVE ALARMS:
{alarms_text}

SINGLE PARAMETER ANOMALIES:
{anomalies_text}

HIGH-RISK COMBINATION ALERTS:
{combinations_text}

Reply ONLY with this JSON — no extra text, no markdown:
{{
    "summary": "2-3 sentences about overall patient status. Mention MEWS/qSOFA scores and exact Time-in-Range alerts if applicable.",
    "concerns": "write all concerns as one single paragraph separated by semicolons, not as a list or array", 
    "trend_assessment": "are things getting better, worse, or stable? mention key trending parameters and velocities"
}}

Rules:
- Do NOT suggest medications or treatments
- Keep it short and clinical
- Prioritize combination alerts and Time-in-Range warnings
- If sensors disconnected mention it"""


async def generate_report(
    patient_mrn: str,
    vital_signs: dict,  # <-- Changed to dict
    alarms: list,
    anomalies: dict,
    combination_alerts: list,
    risk_score: int,
    risk_level: str,
    mews_score: int,    # <-- Added
    qsofa_score: int    # <-- Added
) -> dict:

    prompt = build_prompt(
        patient_mrn,
        vital_signs,
        alarms,
        anomalies.get("anomalies", []),
        combination_alerts,
        risk_score,
        risk_level,
        mews_score,     # <-- Added
        qsofa_score     # <-- Added
    )

    start = time.time()

    try:
        response = await client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2000,
            )
        )
        latency = round(time.time() - start, 2)

        # clean the response text
        response_text = response.text.strip()

        # remove markdown code blocks if Gemini adds them
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        print(f"🤖 Gemini raw response: {response_text}")
        result = json.loads(response_text)

        return {
            "summary": result.get("summary", "Unable to generate summary"),
            "concerns": str(result.get("concerns", "None")) if isinstance(result.get("concerns"), list) else result.get("concerns", "None"),
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