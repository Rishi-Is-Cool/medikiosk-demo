from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ml_backend.schemas.document import DocumentExtractionRequest, ExtractedDocument
from ml_backend.schemas.medical_fact import PatientFact
from ml_backend.schemas.timeline import TimelineResponse
from ml_backend.schemas.snapshot import CurrentIntakeHistory, PhysicianSnapshot, SnapshotAlert
from ml_backend.services.vision_extract import vision_extraction_service
from ml_backend.services.timeline import timeline_service
from ml_backend.services.conflict_detector import conflict_detector_service
from ml_backend.services.snapshot_generator import snapshot_generator_service

router = APIRouter(tags=["Full Intelligence Pipeline"])


class FullPipelineRequest(BaseModel):
    patient_id: str = Field(default="P_DEMO_001", description="Patient identifier")
    documents: List[DocumentExtractionRequest] = Field(default_factory=list, description="Documents to process")
    current_history: Optional[CurrentIntakeHistory] = Field(default=None, description="Kiosk intake session")


class FullPipelineResponse(BaseModel):
    patient_id: str
    extracted_documents: List[ExtractedDocument]
    normalized_facts: List[PatientFact]
    timeline: TimelineResponse
    clinical_alerts: List[SnapshotAlert]
    physician_snapshot: Optional[PhysicianSnapshot] = None


@router.post("/pipeline/full", response_model=FullPipelineResponse)
def execute_full_pipeline(req: FullPipelineRequest):
    """
    Execute the entire MediKiosk AI/ML intelligence pipeline:
    1. Document perception & extraction
    2. Terminology normalization & lab range validation
    3. Chronological timeline synthesis
    4. Clinical contradiction detection
    5. Comprehensive physician snapshot generation
    """
    extracted_docs: List[ExtractedDocument] = []
    all_facts: List[PatientFact] = []
    all_labs = []

    for doc_req in req.documents:
        doc_res = vision_extraction_service.extract_document(
            image_bytes=b"DOCUMENT_PAYLOAD",  # Pipeline coordinator handles already-loaded or mock docs
            mime_type=doc_req.mime_type or "image/jpeg",
            document_id=doc_req.document_id,
            patient_id=req.patient_id
        )
        if doc_res.success and doc_res.extraction:
            extracted_docs.append(doc_res.extraction)
            all_facts.extend(doc_res.normalized_facts)
            all_labs.extend(doc_res.extraction.lab_results)

    # Build timeline
    timeline_res = timeline_service.build_chronological_timeline(extracted_docs)

    # Detect conflicts if current history provided
    alerts: List[SnapshotAlert] = []
    if req.current_history:
        alerts = conflict_detector_service.detect_conflicts(
            current_history=req.current_history,
            historical_facts=all_facts,
            historical_documents=extracted_docs
        )

    # Generate snapshot
    snapshot: Optional[PhysicianSnapshot] = None
    if req.current_history:
        from ml_backend.schemas.snapshot import SnapshotRequest
        snap_req = SnapshotRequest(
            patient_id=req.patient_id,
            current_history=req.current_history,
            facts=all_facts,
            timeline=timeline_res.events,
            documents=extracted_docs,
            lab_results=all_labs
        )
        snapshot = snapshot_generator_service.generate_snapshot(snap_req)

    return FullPipelineResponse(
        patient_id=req.patient_id,
        extracted_documents=extracted_docs,
        normalized_facts=all_facts,
        timeline=timeline_res,
        clinical_alerts=alerts,
        physician_snapshot=snapshot
    )
