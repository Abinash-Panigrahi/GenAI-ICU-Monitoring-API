import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.database import get_db
from app.models.report import Report

router = APIRouter(prefix="/reports", tags=["reports"])

# ==========================================
# 1. GET LATEST REPORT
# ==========================================
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
        "concerns": json.loads(report.concerns) if report.concerns else [],
        "highlight_vitals": json.loads(report.highlight_vitals) if report.highlight_vitals else [],
        "trend_assessment": report.trend_assessment,
        "combination_alerts": report.combination_alerts,
        "anomalies_found": report.anomalies_found,
        "model_used": report.model_used,
        "llm_latency_seconds": report.llm_latency_seconds
    }

# ==========================================
# 2. GET REPORT HISTORY (With Pagination & Time Filter)
# ==========================================
@router.get("/{patient_mrn}/history")
async def get_report_history(
    patient_mrn: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    # 1. Build dynamic filters
    filters = [Report.patient_mrn == patient_mrn]
    
    # 2. Add Range Filters
    if start_time:
        filters.append(Report.generated_at >= start_time) 
    if end_time:
        filters.append(Report.generated_at <= end_time)   
        
    # 3. Count total records matching our filters
    count_query = select(func.count()).where(*filters)
    total_records = (await db.execute(count_query)).scalar()
    
    if total_records == 0:
        raise HTTPException(status_code=404, detail=f"No reports found for patient {patient_mrn} in this time range.")
    
    # 4. Apply pagination math
    offset = (page - 1) * limit
    query = select(Report).where(*filters)\
        .order_by(desc(Report.generated_at))\
        .offset(offset)\
        .limit(limit)
        
    result = await db.execute(query)
    reports = result.scalars().all()
    
    total_pages = (total_records + limit - 1) // limit

    return {
        "patient_mrn": patient_mrn,
        "total_records": total_records,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "data": [
            {
                "id": r.id,
                "generated_at": r.generated_at,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "severity": r.severity_level,
                "summary": r.summary,
                "concerns": json.loads(r.concerns) if r.concerns else [],
                "highlight_vitals": json.loads(r.highlight_vitals) if r.highlight_vitals else [],
                "trend_assessment": r.trend_assessment,
            }
            for r in reports
        ]
    }