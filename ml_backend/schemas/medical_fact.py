from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class FactTypeEnum(str, Enum):
    CONDITION = "condition"
    ALLERGY = "allergy"
    MEDICATION = "medication"
    BLOOD_GROUP = "blood_group"
    PROCEDURE = "procedure"
    SURGERY = "surgery"
    INVESTIGATION = "investigation"
    VITAL = "vital"


class NormalizedTerm(BaseModel):
    raw: str
    normalized: str
    category: Optional[str] = None
    is_known: bool = True

    @property
    def normalized_value(self) -> str:
        return self.normalized


class PatientFact(BaseModel):
    type: FactTypeEnum
    raw_value: str
    normalized_value: str
    date_recorded: Optional[str] = None
    source_document_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
