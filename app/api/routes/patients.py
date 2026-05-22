from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.patient import Patient

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/active")
async def get_active_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Patient).where(Patient.is_active == True)
    )
    patients = result.scalars().all()

    if not patients:
        raise HTTPException(status_code=404, detail="No active patients found")

    return {
        "total": len(patients),
        "patients": [
            {
                "patient_mrn": p.patient_mrn,
                "is_active": p.is_active,
                "created_at": p.created_at
            }
            for p in patients
        ]
    }