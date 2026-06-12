from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ReportResponse(BaseModel):
    id: int
    patient_mrn: str
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    severity_level: Optional[str]
    summary: Optional[str]
    concerns: Optional[str] 
    
    # 👇 ADD THIS LINE 👇
    highlight_vitals: Optional[list] = []
    
    trend_assessment: Optional[str]
    model_used: Optional[str]
    anomalies_found: Optional[list]

    class Config:
        from_attributes = True