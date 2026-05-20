from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VitalsResponse(BaseModel):
    id: int
    patient_mrn: str
    fetched_at: datetime
    window_start: datetime
    window_end: datetime
    vital_signs: Optional[list]
    alarms: Optional[list]

    class Config:
        from_attributes = True