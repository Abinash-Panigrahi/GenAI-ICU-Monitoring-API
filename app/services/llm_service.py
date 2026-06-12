from google import genai
from google.genai import types
import json
import time
from app.config import settings
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception

client = genai.Client(api_key=settings.llm_api_key)

PROMPT_VERSION = "v1.0"
MODEL = "gemini-2.5-flash"

# --- CHANGE 2: Added this function to stop retrying if we get a 400 Error ---
def should_retry_error(exception):
    # If the error string contains '400', stop immediately!
    if "400" in str(exception):
        return False 
    # Otherwise, retry normally (for 503, 500, timeouts)
    return True

def build_prompt(patient_mrn: str, vital_signs: dict, alarms: list, anomalies: list, combination_alerts: list, risk_score: int, risk_level: str, mews_score: int, qsofa_score: int) -> str:
    vitals_text = ""
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
        for alarm in alarms[-30:]:
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

ACTIVE ALARMS (Showing most recent):
{alarms_text}

SINGLE PARAMETER ANOMALIES:
{anomalies_text}

HIGH-RISK COMBINATION ALERTS:
{combinations_text}

Reply ONLY with this JSON — no extra text, no markdown:
{{
    "summary": "2-3 sentences about overall patient status. Mention MEWS/qSOFA scores and exact Time-in-Range alerts if applicable.",
    
    "concerns": [
        {{
            "issue": "Short name of the specific issue (e.g., 'ECG Lead Off', 'SpO2 RR High', 'Bradycardia')",
            "category": "technical or physiological",
            "severity": "warning or critical"
        }}
    ], 
    
    "trend_assessment": "Are things getting better, worse, or stable? Mention key trending parameters. If vital signs arrays are empty, explain WHY based on the technical alarms (e.g., 'Unable to assess trend due to persistent sensor disconnections'). If physiological alarms exist despite missing vitals, use them to infer the trend."
}}

Rules:
- Do NOT suggest medications or treatments
- Keep it short and clinical
- Prioritize combination alerts and Time-in-Range warnings
- If sensors disconnected mention it"""


# --- CHANGE 4: Added the retry_if_exception logic to the decorator ---
@retry(
    wait=wait_random_exponential(multiplier=2, max=40), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception(should_retry_error), 
    reraise=True 
)
async def call_gemini_api(prompt: str):
    return await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2000,
        )
    )


# 2. MAIN CORE FUNCTION: Handles data parsing and the final fallback
async def generate_report(
    patient_mrn: str,
    vital_signs: dict,  
    alarms: list,
    anomalies: dict,
    combination_alerts: list,
    risk_score: int,
    risk_level: str,
    mews_score: int,    
    qsofa_score: int    
) -> dict:

    prompt = build_prompt(
        patient_mrn,
        vital_signs,
        alarms,
        anomalies.get("anomalies", []),
        combination_alerts,
        risk_score,
        risk_level,
        mews_score,     
        qsofa_score     
    )

    start = time.time()

    try:
        response = await call_gemini_api(prompt)
        latency = round(time.time() - start, 2)

        response_text = response.text.strip()
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        print(f"🤖 Gemini raw response: {response_text}")
        result = json.loads(response_text)

        return {
            "summary": result.get("summary", "Unable to generate summary"),
            
            # --- THIS IS THE CRITICAL CHANGE RIGHT HERE ---
            "concerns": result.get("concerns", []),
            
            "trend_assessment": result.get("trend_assessment", "Unable to assess"),
            "model_used": MODEL,
            "prompt_version": PROMPT_VERSION,
            "llm_latency_seconds": latency
        }

    except json.JSONDecodeError:
        return {
            "summary": "Report generation failed — AI response was not in expected format",
            "concerns": [], # Changed to empty list for safety
            "trend_assessment": "Unable to assess",
            "model_used": MODEL,
            "prompt_version": PROMPT_VERSION,
            "llm_latency_seconds": round(time.time() - start, 2)
        }

    except Exception as e:
        return {
            "summary": f"Report generation failed — System Outage ({str(e)})",
            "concerns": [{"issue": "System Error", "category": "technical", "severity": "critical"}], # Changed to mock list for safety
            "trend_assessment": "Unable to assess due to system error",
            "model_used": MODEL,
            "prompt_version": PROMPT_VERSION,
            "llm_latency_seconds": round(time.time() - start, 2)
        }