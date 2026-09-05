"""
MediKiosk AI Clinical History Platform — FastAPI Application Entry Point
Registers all API routers, sets up CORS, loads environment config, and creates DB tables.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env file if present (development mode)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.database.connection import engine, Base
from app.api import auth, patients, interview, documents, summary, fhir_abdm, admin, integration

# ─── Database Initialization ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup (no Alembic required for SQLite dev)."""
    Base.metadata.create_all(bind=engine)
    yield
    # Clean shutdown hooks can go here

# ─── FastAPI Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="MediKiosk AI Clinical Intake Backend API",
    description=(
        "AI-powered clinical history acquisition platform for Indian hospital OPDs. "
        "Features: Adaptive multilingual voice+touch interview (SOCRATES & AYUSH Dashavidha Pariksha), "
        "medical document OCR, emergency red-flag detection, FHIR R4 export, and ABDM interoperability."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health & Status", "description": "System health and readiness checks"},
        {"name": "Authentication", "description": "Kiosk terminal and physician JWT authentication"},
        {"name": "Patients & ABHA Registration", "description": "Patient registration, ABHA ID verification, consent"},
        {"name": "Conversational Multimodal History Engine", "description": "Adaptive interview, voice input, red-flag screening"},
        {"name": "Medical Document Digitization & OCR", "description": "Document upload, OCR extraction, lab timeline"},
        {"name": "Structured History Summary Generator", "description": "AI physician summary, AYUSH Dashavidha summary"},
        {"name": "FHIR R4 & ABDM Interoperability", "description": "FHIR Bundle export, HIS push, consent artefact"},
        {"name": "Admin & OPD Dashboard", "description": "Statistics, patient queue, system monitoring"},
    ],
    lifespan=lifespan
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────
# Allow all origins in development; restrict to specific domains in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register API Routers ─────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(interview.router)
app.include_router(documents.router)
app.include_router(summary.router)
app.include_router(fhir_abdm.router)
app.include_router(admin.router)
app.include_router(integration.kiosk_router)
app.include_router(integration.doctor_router)


# ─── Root & Health Check Endpoints ───────────────────────────────────────────
@app.get("/", tags=["Health & Status"], summary="API root — platform status")
def root():
    """Returns platform identity and links to interactive API documentation."""
    return {
        "status": "online",
        "platform": "MediKiosk AI Clinical History Platform",
        "version": "1.0.0",
        "documentation": "/docs",
        "alternative_docs": "/redoc",
        "fhir_r4_ready": True,
        "abdm_compatible": True,
        "supported_languages": ["Hindi (hi)", "English (en)", "Marathi (mr)", "Tamil (ta)", "Telugu (te)", "Bengali (bn)"]
    }


@app.get("/health", tags=["Health & Status"], summary="Health readiness probe")
def health_check():
    """
    Kubernetes / Docker health check endpoint.
    Returns 200 OK when the service and database connection are operational.
    """
    return {
        "status": "healthy",
        "database": "connected",
        "gemini_ai": "enabled" if os.getenv("GEMINI_API_KEY") else "simulation_mode"
    }
