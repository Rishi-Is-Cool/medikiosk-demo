"""
MediKiosk Backend — Pytest Configuration & Fixtures
Uses a dedicated test SQLite database to prevent test data bleeding into development DB.
"""
import os

# Synthetic OCR is fixture data only; production uploads must report provider
# unavailability rather than invent clinical content.
os.environ["MEDIKIOSK_USE_SYNTHETIC_OCR_FIXTURES"] = "1"

# Tests must be hermetic: they send fake, non-image bytes as "documents" and
# expect the deterministic mock/simulation path every time. If the developer's
# real .env happens to have a live GEMINI_API_KEY (as it may, once someone on
# the team adds one), app.main's load_dotenv() would otherwise leak it in here
# (load_dotenv doesn't override already-set vars, which is exactly what makes
# setting it first — before importing app.main below — the fix) and every
# vision-pipeline test would try a real Gemini call against garbage bytes and
# fail on "unable to process input image" instead of exercising the mock path
# the tests are actually about.
os.environ["GEMINI_API_KEY"] = ""
os.environ["VISION_LLM_API_KEY"] = ""
# Never download or load the Whisper model during tests.
os.environ["WHISPER_PREWARM"] = "0"
# Tests must run against the local SQLite file, never the team's Supabase
# database that the developer's .env points at.
os.environ["DATABASE_URL"] = "sqlite:///./medikiosk_test_app.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base, get_db
from app.database.seed import seed_reference_data
from app.main import app

# ─── Test DB Setup ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_medikiosk.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


def override_get_db():
    """Dependency override: use test DB session for all tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables at start of test session, drop at end.

    The app's own startup lifespan also seeds reference data (demo doctor
    account, advice library) — but it seeds through the production DB
    connection (app.database.connection.SessionLocal), which the `client`
    fixture below never touches once get_db is overridden. So the same seed
    has to run again here, against the actual test database, or the demo
    doctor account tests log in with (and doctor-assignment routing depends
    on) simply doesn't exist in it.
    """
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        seed_reference_data(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    # Clean up test DB file
    if os.path.exists("./test_medikiosk.db"):
        os.remove("./test_medikiosk.db")


@pytest.fixture(scope="module")
def client(setup_test_database):
    """Module-scoped FastAPI TestClient with DB override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def registered_patient(client):
    """Creates a standard test patient and returns the patient_id."""
    payload = {
        "name": "Meera Krishnan",
        "age": 38,
        "gender": "Female",
        "language": "hi",
        "abha_id": "91-9999-8888-7777",
        "phone": "9000000001",
        "consent_granted": True
    }
    response = client.post("/api/patients/register", json=payload)
    assert response.status_code == 201
    return response.json()["patient_id"]
