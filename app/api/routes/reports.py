from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.report import Report

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{patient_mrn}")
async def get_latest_report(patient_mrn: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Report)
        .where(Report.patient_mrn == patient_mrn)
        .order_by(desc(Report.generated_at))
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail=f"No report found for patient {patient_mrn}")

    return {
        "patient_mrn": report.patient_mrn,
        "generated_at": report.generated_at,
        "risk_score": report.risk_score,
        "risk_level": report.risk_level,
        "severity": report.severity_level,
        "summary": report.summary,
        "concerns": report.concerns,
        "trend_assessment": report.trend_assessment,
        "combination_alerts": report.combination_alerts,
        "anomalies_found": report.anomalies_found,
        "model_used": report.model_used,
        "llm_latency_seconds": report.llm_latency_seconds
    }

@router.get("/{patient_mrn}/history")
async def get_report_history(patient_mrn: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Report)
        .where(Report.patient_mrn == patient_mrn)
        .order_by(desc(Report.generated_at))
        .limit(limit)
    )
    reports = result.scalars().all()

    if not reports:
        raise HTTPException(status_code=404, detail=f"No reports found for patient {patient_mrn}")

    return {
        "patient_mrn": patient_mrn,
        "total": len(reports),
        "reports": [
            {
                "id": r.id,
                "generated_at": r.generated_at,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "severity": r.severity_level,
                "summary": r.summary,
                "concerns": r.concerns,
                "trend_assessment": r.trend_assessment,
            }
            for r in reports
        ]
    }