# pyrefly: ignore [missing-import]
from fastapi import FastAPI

app = FastAPI(
    title="ICU Monitor API",
    description="AI-powered ICU patient monitoring system",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "ICU Monitor is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}