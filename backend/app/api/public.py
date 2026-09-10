"""
MediKiosk Backend — public, unauthenticated patient-facing pages.

This is the one router in the whole backend a patient's own phone hits
directly, with no login — that's the point of a QR code. Everything here is
scoped by an unguessable share_token (generated at finalize time), never by
a sequential/guessable id, and returns only what that one visit's own patient
sheet already shows them, nothing more.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import AdviceLibraryEntry, ClinicalFact, DoctorProfile, Encounter, LedgerEntry, Patient
from app.services.integration import parse_follow_up_days

router = APIRouter(prefix="/api/public", tags=["Public Patient Pages"])


def _escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@router.get("/visit/{share_token}", response_class=HTMLResponse)
def view_shared_visit(share_token: str, db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.share_token == share_token).first()
    if not encounter:
        raise HTTPException(404, "This link is invalid or has expired")
    patient = db.query(Patient).filter(Patient.patient_id == encounter.patient_id).first()
    doctor = db.query(DoctorProfile).filter(DoctorProfile.username == encounter.assigned_doctor_username).first()
    ledger = (db.query(LedgerEntry).filter(LedgerEntry.encounter_id == encounter.encounter_id)
              .order_by(LedgerEntry.created_at.desc()).first())
    medications = [f.raw_value for f in db.query(ClinicalFact)
                   .filter(ClinicalFact.encounter_id == encounter.encounter_id, ClinicalFact.fact_type == "medication").all()]

    bilingual = bool(patient and patient.language == "hi")
    advice_rows = []
    if ledger and ledger.advice:
        advice_ids = [a.get("id") if isinstance(a, dict) else a for a in ledger.advice]
        entries = db.query(AdviceLibraryEntry).filter(AdviceLibraryEntry.advice_id.in_(advice_ids)).all()
        advice_rows = [(e.text, e.text_hi if bilingual else None) for e in entries]

    follow_up_date = None
    if ledger and ledger.follow_up_required and ledger.follow_up_timeframe:
        days = parse_follow_up_days(ledger.follow_up_timeframe)
        if days is not None:
            follow_up_date = (date.today() + timedelta(days=days)).isoformat()

    if ledger and ledger.medicines:
        med_lines = [f"{m.get('name', '')} — {m.get('dosage', '')} {m.get('frequency', '')}".strip(" —") for m in ledger.medicines]
    else:
        med_lines = medications
    med_items = "".join(f"<li>{_escape(m)}</li>" for m in med_lines)
    advice_items = "".join(
        f"<li><b>{_escape(en)}</b>{f'<br><span lang=\"hi\">{_escape(hi)}</span>' if hi else ''}</li>"
        for en, hi in advice_rows
    )
    notes_block = f'<section><h3>Doctor\'s note</h3><p>{_escape(ledger.notes)}</p></section>' if ledger and ledger.notes else ""
    follow_up_block = f'<section><h3>Come back on</h3><p>{follow_up_date}</p></section>' if follow_up_date else ""

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visit summary — {_escape(patient.name if patient else '')}</title>
<style>
:root {{ color-scheme: light; }}
body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 0 auto; padding: 20px; color: #1c1c1c; background: #ffffff; }}
h1 {{ font-size: 1.1rem; }} h3 {{ font-size: 0.95rem; margin-bottom: 4px; }}
section {{ margin-top: 18px; padding-top: 14px; border-top: 1px solid #ddd; }}
.clinic {{ color: #0f6f5c; font-weight: bold; }}
li {{ margin-bottom: 8px; }}
</style></head>
<body>
<p class="clinic">{_escape(doctor.clinic_name if doctor else 'MediKiosk')}</p>
<h1>{_escape(patient.name if patient else 'Patient')} — visit on {encounter.finalized_at.strftime('%d %b %Y') if encounter.finalized_at else ''}</h1>
<p>{_escape(encounter.chief_complaint or '')}</p>
<section><h3>Medicines</h3><ul>{med_items or '<li>None recorded</li>'}</ul></section>
<section><h3>Advice</h3><ul>{advice_items or '<li>None recorded</li>'}</ul></section>
{follow_up_block}
{notes_block}
<section><p style="color:#888; font-size:0.8rem;">This is a summary of one visit, shared by your doctor. It is not your full medical record.</p></section>
</body></html>"""
    return HTMLResponse(content=html)
