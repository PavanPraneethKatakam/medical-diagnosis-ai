"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict


class PredictRequest(BaseModel):
    """Request model for /agents/predict endpoint."""
    patient_id: int = Field(..., gt=0, description="Patient ID (must be positive)")
    clinician_comment: Optional[str] = Field(None, max_length=1000, description="Optional clinician input")
    
    @validator('clinician_comment')
    def validate_comment(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class RefineRequest(BaseModel):
    """Request model for /agents/refine endpoint."""
    patient_id: int = Field(..., gt=0)
    feedback: Dict = Field(..., description="Feedback with action, from, to, reason")
    clinician_comment: Optional[str] = Field(None, max_length=1000, description="Optional clinician input")
    
    @validator('feedback')
    def validate_feedback(cls, v):
        required_keys = {'action', 'from', 'to', 'reason'}
        if not all(key in v for key in required_keys):
            raise ValueError(f"Feedback must contain: {required_keys}")
        
        valid_actions = {'add_edge', 'remove_edge', 'reverse_edge'}
        if v['action'] not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")
        
        return v


class ChatRequest(BaseModel):
    """Request model for /agents/chat endpoint."""
    patient_id: int = Field(..., gt=0)
    message: str = Field(..., min_length=1, max_length=1000, description="Chat message")
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class UploadDocRequest(BaseModel):
    """Request model for document upload metadata."""
    disease_code: Optional[str] = Field(None, max_length=10, description="ICD-10 disease code")
    
    @validator('disease_code')
    def validate_disease_code(cls, v):
        if v is not None:
            v = v.strip().upper()
            if len(v) == 0:
                return None
        return v


class PredictionResponse(BaseModel):
    """Response model for predictions."""
    predictions: List[Dict]
    explanation: str
    evidence: List[Dict]
    dag: Dict
    fallback: bool


class ChatResponse(BaseModel):
    """Response model for chat."""
    reply: str
    conversation_id: int
    patient_id: int


class UploadResponse(BaseModel):
    """Response model for document upload."""
    message: str
    doc_ids: List[int]
    preview_snippets: List[Dict]
    filename: str
    disease_code: Optional[str]
