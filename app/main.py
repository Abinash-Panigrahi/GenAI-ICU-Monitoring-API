from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import engine, get_db
from app.services.report_generator import process_patient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        print("✅ Database connected successfully")
    yield
    # shutdown
    await engine.dispose()
    print("Database disconnected")

app = FastAPI(
    title="ICU Monitor API",
    description="AI-powered ICU patient monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "ICU Monitor is running"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.app_env,
        "debug": settings.debug
    }

@app.get("/test/{patient_mrn}")
async def test_pipeline(patient_mrn: str, db: AsyncSession = Depends(get_db)):
    report = await process_patient(patient_mrn, db)
    return {
        "message": "Report generated successfully",
        "patient_mrn": patient_mrn,
        "severity": report.severity_level,
        "summary": report.summary,
        "concerns": report.concerns,
        "trend_assessment": report.trend_assessment,
        "model_used": report.model_used,
        "llm_latency_seconds": report.llm_latency_seconds
    }