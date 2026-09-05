"""
MediKiosk Backend — Pytest Configuration & Fixtures
Uses a dedicated test SQLite database to prevent test data bleeding into development DB.
"""
import os

# Synthetic OCR is fixture data only; production uploads must report provider
# unavailability rather than invent clinical content.
os.environ["MEDIKIOSK_USE_SYNTHETIC_OCR_FIXTURES"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base, get_db
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
    """Create all tables at start of test session, drop at end."""
    Base.metadata.create_all(bind=test_engine)
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
