from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TimelineEventType(str, Enum):
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    INVESTIGATION = "investigation"
    HOSPITALIZATION = "hospitalization"
    PROCEDURE = "procedure"
    SURGERY = "surgery"
    CONSULTATION = "consultation"
    DISCHARGE = "discharge"
    FOLLOW_UP = "follow_up"


class TimelineEvent(BaseModel):
    event_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD or YYYY format. null if unknown.")
    event_type: TimelineEventType
    summary: str = Field(..., description="Concise human-readable event summary")
    source_document_id: str
    source_document_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_date_inferred: bool = False


class TimelineResponse(BaseModel):
    patient_id: Optional[str] = None
    total_events: int
    events: List[TimelineEvent] = Field(default_factory=list)
