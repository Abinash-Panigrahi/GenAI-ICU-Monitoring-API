from google import genai
import json
import time
from app.config import settings

client = genai.Client(api_key=settings.llm_api_key)

PROMPT_VERSION = "v1.0"
MODEL = "gemini-2.5-flash-preview-04-17"

def build_prompt(patient_mrn: str, vital_signs: list, alarms: list, anomalies: list) -> str:
    
    # format vitals into simple text
    if vital_signs:
        vitals_text = "\n".join(
            f"- {v['parameterName']}: {v['value']} {v['unit']}"
            for v in vital_signs
        )
    else:
        vitals_text = "No valid vitals — all sensors may be disconnected"

    # format alarms into simple text
    if alarms:
        alarms_text = "\n".join(
            f"- {a['alarm_text']}"
            for a in alarms
        )
    else:
        alarms_text = "No active alarms"

    # format anomalies into simple text
    if anomalies:
        anomalies_text = "\n".join(
            f"- {a['parameter']}: {a['issue']}"
            for a in anomalies
        )
    else:
        anomalies_text = "No anomalies detected"

    return f"""You are helping ICU doctors and nurses monitor patients.
Analyze the vitals below and write a short clinical report.

Patient: {patient_mrn}

VITALS:
{vitals_text}

ALARMS:
{alarms_text}

DETECTED ISSUES:
{anomalies_text}

Reply ONLY with this JSON — no extra text, no markdown:
{{
    "summary": "2-3 sentences about overall patient status",
    "concerns": "list specific concerns or write None if patient is stable",
    "trend_assessment": "are things getting better, worse, or stable?"
}}

Important:
- Do NOT suggest medications or treatments
- Keep it short and clinical
- If sensors are disconnected, mention it clearly"""


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