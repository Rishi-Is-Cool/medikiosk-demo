from fastapi import APIRouter

from ml_backend.routers.documents import router as documents_router
from ml_backend.routers.validation import router as validation_router
from ml_backend.routers.timeline import router as timeline_router
from ml_backend.routers.snapshot import router as snapshot_router
from ml_backend.routers.doctor import router as doctor_router
from ml_backend.routers.pipeline import router as pipeline_router

# Unified ML router mounted at prefix /ml
api_router = APIRouter(prefix="/ml")

api_router.include_router(documents_router)
api_router.include_router(validation_router)
api_router.include_router(timeline_router)
api_router.include_router(snapshot_router)
api_router.include_router(doctor_router)
api_router.include_router(pipeline_router)

__all__ = ["api_router"]
