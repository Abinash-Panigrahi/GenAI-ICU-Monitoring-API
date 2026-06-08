from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import engine, get_db
from app.services.report_generator import process_patient
from app.api.routes import reports, patients
from app.api.routes import reports, patients
from scheduler.jobs import start_scheduler, stop_scheduler
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        print("✅ Database connected successfully")
    start_scheduler()
    yield
    # shutdown
    stop_scheduler()
    await engine.dispose()
    print("Database disconnected")

app = FastAPI(
    title="ICU Monitor API",
    description="AI-powered ICU patient monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all frontend domains to connect
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, and the tricky OPTIONS method!
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(patients.router)

@app.get("/")
async def root():
    return {"message": "ICU Monitor is running"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.app_env,
        "debug": settings.debug,
        "use_test_date": settings.use_test_date,
        "test_start_date": settings.test_start_date
    }

@app.get("/test/{patient_mrn}")
async def test_pipeline(patient_mrn: str, db: AsyncSession = Depends(get_db)):
    report = await process_patient(patient_mrn, db)
    return {
        "message": "Report generated successfully",
        "patient_mrn": patient_mrn,
        "severity": report.severity_level,
        "risk_score": report.risk_score,
        "risk_level": report.risk_level,
        "combination_alerts": report.combination_alerts,
        "summary": report.summary,
        "concerns": report.concerns,
        "trend_assessment": report.trend_assessment,
        "model_used": report.model_used,
        "llm_latency_seconds": report.llm_latency_seconds
    }