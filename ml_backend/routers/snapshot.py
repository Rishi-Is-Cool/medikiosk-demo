from fastapi import APIRouter
from ml_backend.schemas.snapshot import SnapshotRequest, PhysicianSnapshot
from ml_backend.services.snapshot_generator import snapshot_generator_service

router = APIRouter(tags=["Physician Snapshot"])


@router.post("/snapshot/generate", response_model=PhysicianSnapshot)
def generate_snapshot(req: SnapshotRequest):
    """
    Synthesize a structured 12-section physician intake snapshot combining current kiosk intake with historical document records.
    Every clinical assertion carries explicit source provenance citations.
    """
    return snapshot_generator_service.generate_snapshot(req)
