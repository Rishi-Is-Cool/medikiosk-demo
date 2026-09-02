from typing import List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ml_backend.schemas.document import ExtractedDocument
from ml_backend.schemas.timeline import TimelineResponse
from ml_backend.services.timeline import timeline_service

router = APIRouter(tags=["Chronological Timeline"])


class TimelineBuildRequest(BaseModel):
    documents: List[ExtractedDocument] = Field(..., description="List of extracted documents to synthesize into timeline")


@router.post("/timeline/build", response_model=TimelineResponse)
def build_timeline(req: TimelineBuildRequest):
    """
    Synthesize an aggregated, chronologically sorted patient medical event timeline across all uploaded documents.
    """
    return timeline_service.build_chronological_timeline(req.documents)
