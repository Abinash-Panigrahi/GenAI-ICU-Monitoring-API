from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Float
from sqlalchemy.sql import func
from app.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_mrn = Column(String, nullable=False, index=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    
    # rules engine output
    anomalies_found = Column(JSON, nullable=True)
    severity_level = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    combination_alerts = Column(JSON, nullable=True)
    
    # llm output
    summary = Column(Text, nullable=True)
    concerns = Column(Text, nullable=True)
    trend_assessment = Column(Text, nullable=True)
    
    # metadata
    model_used = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    llm_latency_seconds = Column(Float, nullable=True)