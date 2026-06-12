import json  # <--- 1. ADD THIS IMPORT AT THE TOP
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vitals import Vitals
from app.models.report import Report
from app.services.vitals_fetcher import fetch_patient_data
from app.services.rules_engine import analyze_vitals
from app.services.llm_service import generate_report
from tests.mock_data import MOCK_PATIENTS


async def process_patient(patient_mrn: str, db: AsyncSession):
    
    # step 1 — fetch vitals and alarms from hardware API
    raw_data = await fetch_patient_data(patient_mrn)

    vital_signs = raw_data["vital_signs"]
    alarms = raw_data["alarms"]
    window_start = raw_data["window_start"]
    window_end = raw_data["window_end"]

    # --- CLEAN TEST HOOK ---
    if patient_mrn in MOCK_PATIENTS:
        print(f"⚠️ INJECTING MOCK DATA FOR: {patient_mrn}")
        vital_signs = MOCK_PATIENTS[patient_mrn]

    # step 2 — save raw vitals to database
    vitals_record = Vitals(
        patient_mrn=patient_mrn,
        vital_signs=vital_signs,
        alarms=alarms,
        window_start=window_start,
        window_end=window_end
    )
    db.add(vitals_record)
    await db.commit()

    # step 3 — run rules engine
    anomalies = analyze_vitals(vital_signs, alarms)

    # step 4 — generate LLM report
    llm_output = await generate_report(
        patient_mrn=patient_mrn,
        vital_signs=vital_signs,
        alarms=alarms,
        anomalies=anomalies,
        combination_alerts=anomalies["combination_alerts"],
        risk_score=anomalies["risk_score"],
        risk_level=anomalies["risk_level"],
        mews_score=anomalies["mews_score"],
        qsofa_score=anomalies["qsofa_score"]
    )

    # step 5 — save report to database
    report = Report(
        patient_mrn=patient_mrn,
        window_start=window_start,
        window_end=window_end,
        anomalies_found=anomalies["anomalies"],
        severity_level=anomalies["severity"],
        risk_score=anomalies["risk_score"],
        risk_level=anomalies["risk_level"],
        combination_alerts=anomalies["combination_alerts"],
        
        # --- NEW MEDICAL DATA STORED HERE ---
        mews_score=anomalies["mews_score"],
        qsofa_score=anomalies["qsofa_score"],
        organ_system_summary=vital_signs,
        # ------------------------------------
        
        summary=llm_output["summary"],
        
        # <--- 2. ADD json.dumps() RIGHT HERE --->
        concerns=json.dumps(llm_output["concerns"]), 
        
        trend_assessment=llm_output["trend_assessment"],
        model_used=llm_output["model_used"],
        prompt_version=llm_output["prompt_version"],
        llm_latency_seconds=llm_output["llm_latency_seconds"]
    )
    db.add(report)
    await db.commit()

    return report