"""
Main FastAPI Application for Agentic Medical Diagnosis System

This is the new entry point that uses the agents-based architecture.
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3
import uvicorn

# Import new agents router
from api.agents_router import router as agents_router
from agents.model_pool import get_model_pool

app = FastAPI(
    title="Agentic Medical Diagnosis System",
    description="AI-powered medical diagnosis with multi-agent workflow",
    version="2.0.0"
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "database/medical_knowledge.db"


@app.on_event("startup")
async def startup_event():
    """
    Preload all AI models at server startup for faster first response.
    """
    print("\n" + "=" * 60)
    print("🚀 Starting Agentic Medical Diagnosis System")
    print("=" * 60)
    
    # Preload models
    model_pool = get_model_pool()
    
    # Preload embedding model
    model_pool.load_embedding_model("all-MiniLM-L6-v2")
    
    # Preload SLM model
    model_pool.load_slm_model("google/flan-t5-small")
    
    # Warmup models with dummy inference
    model_pool.warmup_models()
    
    print("=" * 60)
    print("✅ All models loaded and ready!")
    print("=" * 60 + "\n")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for all unhandled errors.
    
    Returns JSON error response with details.
    """
    import traceback
    
    # Log the error
    print(f"❌ ERROR: {exc}")
    traceback.print_exc()
    
    # Return JSON error response
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": str(request.url)
        }
    )


# Include routers
app.include_router(agents_router, prefix="/agents", tags=["agents"])

# Mount static files AFTER routers to avoid conflicts
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve frontend at root
@app.get("/")
async def root():
    """Serve the frontend application."""
    return FileResponse("frontend/index.html")


# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/medical_knowledge.db")


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Pydantic models
class Patient(BaseModel):
    patient_id: int
    name: str
    dob: str
    gender: str


class Visit(BaseModel):
    visit_id: int
    visit_date: str
    diagnosis_code: str
    diagnosis_name: str


class Disease(BaseModel):
    disease_code: str
    disease_name: str


@app.get("/")
async def root():
    """Serve the frontend HTML page."""
    return FileResponse("frontend/index.html")


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Agentic Medical Diagnosis System",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "patients": "/patients",
            "predict": "/agents/predict",
            "refine": "/agents/refine",
            "dag": "/agents/dag/{patient_id}",
            "chat": "/agents/chat",
            "upload": "/agents/upload_doc",
            "health": "/health"
        }
    }


@app.get("/patients", response_model=List[Patient])
def get_patients():
    """Get all patients."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id, name, dob, gender FROM patients")
    rows = cursor.fetchall()
    patients = [
        {
            "patient_id": row[0],
            "name": row[1],
            "dob": row[2],
            "gender": row[3]
        }
        for row in rows
    ]
    conn.close()
    return patients


@app.get("/patients/{patient_id}/history", response_model=List[Visit])
async def get_patient_history(patient_id: int):
    """Get patient diagnosis history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT v.visit_id, v.visit_date, d.disease_code, d.disease_name
        FROM visits v
        LEFT JOIN diagnoses d ON v.visit_id = d.visit_id
        WHERE v.patient_id = ?
        ORDER BY v.visit_date
    """
    cursor.execute(query, (patient_id,))
    rows = cursor.fetchall()
    
    history = []
    for row in rows:
        # Only include visits that have diagnoses
        if row[2] is not None:  # disease_code exists
            history.append({
                "visit_id": row[0],
                "visit_date": row[1],
                "diagnosis_code": row[2],
                "diagnosis_name": row[3]
            })
    
    conn.close()
    return history


@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patients")
        patient_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "patient_count": patient_count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
