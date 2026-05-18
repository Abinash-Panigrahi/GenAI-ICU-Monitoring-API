# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from app.config import settings
from app.database import engine

app = FastAPI(
    title="ICU Monitor API",
    description="AI-powered ICU patient monitoring system",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        print("✅ Database connected successfully")

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    print("❌ Database disconnected")

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