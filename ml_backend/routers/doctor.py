from fastapi import APIRouter
from ml_backend.schemas.qa import DoctorQARequest, DoctorQAResponse
from ml_backend.services.doctor_qa import doctor_qa_service

router = APIRouter(tags=["Doctor Q&A Assistant"])


@router.post("/doctor/qa", response_model=DoctorQAResponse)
def answer_doctor_query(req: DoctorQARequest):
    """
    Doctor clinical Q&A inquiry assistant:
    Retrieves grounded evidence from extracted patient memory and generates structured answers with strict document provenance.
    """
    return doctor_qa_service.answer_question(req)
