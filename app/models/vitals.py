from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class Vitals(Base):
    __tablename__ = "vitals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_mrn = Column(String, nullable=False, index=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    vital_signs = Column(JSON, nullable=True)
    alarms = Column(JSON, nullable=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)