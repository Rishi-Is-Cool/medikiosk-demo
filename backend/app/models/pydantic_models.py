from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PatientCreate(BaseModel):
    name: str = Field(..., example="Rajesh Sharma")
    age: int = Field(..., example=45)
    gender: str = Field(..., example="Male")
    language: Optional[str] = Field("hi", example="hi")
    abha_id: Optional[str] = Field(None, example="91-1234-5678-9012")
    phone: Optional[str] = Field(None, example="9876543210")
    consent_granted: bool = Field(True, example=True)

class PatientResponse(BaseModel):
    patient_id: str
    name: str
    age: int
    gender: str
    language: str
    abha_id: Optional[str] = None
    phone: Optional[str] = None
    consent_granted: bool

    class Config:
        from_attributes = True


class QuestionOption(BaseModel):
    label: str
    value: str

class NextQuestionRequest(BaseModel):
    patient_id: str
    current_step: int
    answers: Dict[str, Any] = Field(default_factory=dict)
    department_mode: Optional[str] = "Allopathy" # Allopathy or AYUSH

class NextQuestionResponse(BaseModel):
    question_id: str
    step: int
    total_steps: int
    question_text: Dict[str, str]  # Multilingual: {"en": "...", "hi": "...", "mr": "..."}
    audio_prompt_url: Optional[str] = None
    input_type: str  # text, options, multi_select, voice_or_text
    options: Optional[List[QuestionOption]] = None
    is_complete: bool = False
    red_flag_alert: Optional[Dict[str, Any]] = None


class AnswerSubmitRequest(BaseModel):
    patient_id: str
    question_id: str
    step: int
    answer_text: Optional[str] = None
    selected_options: Optional[List[str]] = None
    department_mode: Optional[str] = "Allopathy"


class RedFlagAlert(BaseModel):
    is_emergency: bool
    title: str
    message: str
    triage_priority: str  # P1_CRITICAL, P2_URGENT, P3_ROUTINE
    recommended_action: str


class DocumentExtractResponse(BaseModel):
    document_id: str
    patient_id: str
    document_type: str
    document_date: Optional[str] = None
    ocr_text: str
    extracted_diagnoses: List[str] = []
    extracted_medications: List[Dict[str, str]] = []
    lab_results: List[Dict[str, Any]] = []


class ClinicalSummaryResponse(BaseModel):
    patient_id: str
    history_id: str
    patient_name: str
    age: int
    gender: str
    department_mode: str
    chief_complaint: str
    hpi: str
    past_history: str
    surgical_history: str
    allergies: str
    medications: str
    family_history: str
    personal_history: str
    review_of_systems: str
    ayush_dashavidha_summary: Optional[Dict[str, Any]] = None
    lab_timeline_summary: List[Dict[str, Any]] = []
    red_flags: List[Dict[str, Any]] = []
    formatted_summary_markdown: str
    audio_summary_text: str
    status: str  # draft / confirmed


class SummaryUpdateRequest(BaseModel):
    chief_complaint: Optional[str] = None
    hpi: Optional[str] = None
    past_history: Optional[str] = None
    medications: Optional[str] = None
    allergies: Optional[str] = None
    status: Optional[str] = "confirmed"


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


# Integrated kiosk and doctor-console contracts.  They intentionally use
# opaque session/encounter references instead of exposing numeric database IDs.
class RegistrationRequest(BaseModel):
    identity_method: str = "new"
    identifier: Optional[str] = None
    language: str = "en"
    new_patient: Optional[Dict[str, str]] = None


class ConsentSubmission(BaseModel):
    session_id: str
    granted: List[str] = Field(default_factory=list)
    declined: List[str] = Field(default_factory=list)
    language: str = "en"
    audio_explanation_played: bool = False


class StartIntakeRequestV2(BaseModel):
    session_id: str
    history_mode: str
    chief_complaint: str
    chief_complaint_text: Optional[str] = None
    language: str = "en"


class AnswerPayload(BaseModel):
    source: str
    values: List[str] = Field(default_factory=list)
    text: Optional[str] = None


class SubmitIntakeAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: AnswerPayload
    language: str = "en"
    mode: Optional[str] = None


class LedgerRequest(BaseModel):
    treatment_change: bool = False
    previous_treatment: Optional[str] = None
    new_treatment: Optional[str] = None
    deviation_reason: Optional[str] = None
    doctor_rationale: Optional[str] = None
    advice: List[Dict[str, Any]] = Field(default_factory=list)
    follow_up_required: bool = False
    follow_up_timeframe: Optional[str] = None
    doctor_confirmed: bool = False


class DoctorQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
