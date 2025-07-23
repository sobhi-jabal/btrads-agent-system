"""Agent-related models"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ValidationStatus(str, Enum):
    """Validation status for agent results"""
    PENDING = "pending"
    APPROVED = "approved"
    MODIFIED = "modified"
    FLAGGED = "flagged"

class HighlightedSource(BaseModel):
    """Highlighted source text from clinical note"""
    text: str
    start_char: int
    end_char: int
    confidence: float = Field(ge=0, le=1)
    
class MissingInfo(BaseModel):
    """Missing information tracking"""
    field: str
    reason: str
    clinical_impact: str
    suggested_fallback: Optional[str] = None

class AgentResult(BaseModel):
    """Result from an individual agent"""
    agent_id: str
    node_id: str
    patient_id: str
    timestamp: datetime
    
    # Extraction results
    extracted_value: Any
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    
    # Source tracking
    source_highlights: List[HighlightedSource] = []
    
    # Validation
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validated_value: Optional[Any] = None
    validator_notes: Optional[str] = None
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    
    # Missing information
    missing_info: List[MissingInfo] = []
    
    # Metadata
    processing_time_ms: int
    llm_model: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "prior_assessment_agent",
                "node_id": "node_1_suitable_prior",
                "patient_id": "PT001",
                "timestamp": "2024-01-20T10:30:00Z",
                "extracted_value": "yes",
                "confidence": 0.95,
                "reasoning": "Prior MRI from 3 months ago available for comparison",
                "source_highlights": [{
                    "text": "Comparison is made with prior MRI dated 10/15/2023",
                    "start_char": 150,
                    "end_char": 201,
                    "confidence": 0.98
                }],
                "validation_status": "pending",
                "processing_time_ms": 1250,
                "llm_model": "llama3:8b"
            }
        }

class AgentValidationRequest(BaseModel):
    """Request to validate an agent result"""
    result_id: str
    validated_value: Any
    notes: Optional[str] = None
    validator_id: str