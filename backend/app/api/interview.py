"""
MediKiosk Backend — Conversational Multimodal History Engine API
Endpoints for adaptive interview flow, voice audio input, and session management.
"""
import uuid
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import Patient, ClinicalHistory
from app.models.pydantic_models import (
    NextQuestionRequest, NextQuestionResponse, AnswerSubmitRequest
)
from app.ai.question_engine import question_engine
from app.ai.speech_to_text import stt_engine
from app.ai.red_flag_detector import red_flag_detector

router = APIRouter(prefix="/api/interview", tags=["Conversational Multimodal History Engine"])


@router.post(
    "/next-question",
    response_model=NextQuestionResponse,
    summary="Get next adaptive interview question for patient kiosk"
)
def get_next_question(req: NextQuestionRequest, db: Session = Depends(get_db)):
    """
    Returns the next structured question in the adaptive clinical history interview.
    Performs real-time red flag screening on all answers collected so far.
    Supports both Allopathy (SOCRATES) and AYUSH (Dashavidha Pariksha) modes.
    """
    patient = db.query(Patient).filter(Patient.patient_id == req.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient session not found")

    response = question_engine.get_next_question(
        current_step=req.current_step,
        answers=req.answers,
        department_mode=req.department_mode or "Allopathy"
    )
    return response


@router.post(
    "/submit-answer",
    summary="Submit a patient's answer for a specific interview step"
)
def submit_answer(req: AnswerSubmitRequest, db: Session = Depends(get_db)):
    """
    Records an answer and checks for emergency red flags immediately.
    Returns next_step, red_flag_detected status, and the list of any detected alerts.
    """
    patient = db.query(Patient).filter(Patient.patient_id == req.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Combine text or option answers for red flag analysis
    answer_val = req.answer_text or (", ".join(req.selected_options) if req.selected_options else "")
    text_corpus = f"{req.question_id}: {answer_val}"
    red_flags = red_flag_detector.check_red_flags(text_corpus)
    is_emergency = any(rf["priority"] == "P1_CRITICAL" for rf in red_flags)

    return {
        "success": True,
        "patient_id": req.patient_id,
        "question_id": req.question_id,
        "step_completed": req.step,
        "next_step": req.step + 1,
        "answer_recorded": answer_val,
        "red_flag_detected": len(red_flags) > 0,
        "is_emergency": is_emergency,
        "red_flags": red_flags
    }


@router.post(
    "/voice-input",
    summary="Process voice audio input from kiosk microphone (multilingual ASR)"
)
async def process_voice_input(
    patient_id: str = Form(..., description="Patient ID from registration"),
    language: str = Form("hi", description="ISO 639-1 language code: hi/en/mr/ta/te/bn"),
    audio_file: UploadFile = File(..., description="Audio file (WAV/MP3/OGG/WEBM)")
):
    """
    Accepts audio file from kiosk microphone, runs Indian-language ASR,
    then screens the transcript for emergency red flags immediately.
    Supports: Hindi (hi), English (en), Marathi (mr), Tamil (ta), Telugu (te), Bengali (bn).
    """
    audio_bytes = await audio_file.read()
    stt_result = stt_engine.transcribe_audio(audio_bytes, language=language)

    if not stt_result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Speech transcription failed: {stt_result.get('message', 'Unknown error')}"
        )

    # Immediate red flag screening on voice transcript
    red_flags = red_flag_detector.check_red_flags(stt_result["transcript"])
    is_emergency = any(rf["priority"] == "P1_CRITICAL" for rf in red_flags)

    return {
        "patient_id": patient_id,
        "transcript": stt_result["transcript"],
        "confidence": stt_result["confidence"],
        "language": stt_result["language"],
        "engine": stt_result.get("engine", "MediKiosk ASR"),
        "red_flag_detected": len(red_flags) > 0,
        "is_emergency": is_emergency,
        "red_flags": red_flags
    }


@router.get(
    "/questions/{department_mode}",
    summary="Get all question steps for a department mode (pre-loading for kiosk)"
)
def get_all_questions(department_mode: str = "Allopathy"):
    """
    Returns the full list of all interview questions for a given mode.
    Used by the kiosk frontend to pre-load questions and enable offline capability.
    """
    if department_mode.upper() not in ["ALLOPATHY", "AYUSH"]:
        raise HTTPException(
            status_code=400,
            detail="department_mode must be 'Allopathy' or 'AYUSH'"
        )
    steps = question_engine.get_all_steps(department_mode)
    return {
        "department_mode": department_mode,
        "total_steps": len(steps),
        "questions": steps
    }


@router.get(
    "/audio-prompt/{question_id}",
    summary="Get audio prompt text for a specific question (TTS generation)"
)
def get_audio_prompt(question_id: str, language: str = "hi"):
    """
    Returns the audio prompt text for a given question_id in the requested language.
    The kiosk frontend uses this for Text-to-Speech playback guidance.
    """
    # Search across both step lists
    from app.ai.question_engine import ALLOPATHY_STEPS, AYUSH_STEPS
    all_steps = ALLOPATHY_STEPS + AYUSH_STEPS

    for step in all_steps:
        if step["id"] == question_id:
            prompt_text = step["question_text"].get(
                language,
                step["question_text"].get("en", "Please answer the following question.")
            )
            return {
                "question_id": question_id,
                "language": language,
                "audio_prompt_text": prompt_text,
                "tts_ready": True
            }

    raise HTTPException(status_code=404, detail=f"Question ID '{question_id}' not found")
