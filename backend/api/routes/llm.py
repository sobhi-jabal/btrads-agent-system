"""LLM extraction API routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any
import logging

from services.ollama_service import OllamaExtractionService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Ollama service
ollama_service = OllamaExtractionService(model="phi4:14b")


class ExtractionRequest(BaseModel):
    """Request model for LLM extraction"""
    clinical_note: str
    extraction_type: Literal["medications", "radiation_date", "suitable_prior", "imaging_assessment", 
                           "on_medications", "avastin_response", "steroid_effects", "time_since_xrt"]
    model: Optional[str] = "phi4:14b"
    context_data: Optional[Dict[str, Any]] = None


class ExtractionResponse(BaseModel):
    """Response model for LLM extraction"""
    data: Dict[str, Any]
    evidence: list
    confidence: float
    processing_time: float
    method: str = "llm"
    model: str
    error: Optional[str] = None


@router.post("/extract", response_model=ExtractionResponse)
async def extract_information(request: ExtractionRequest):
    """
    Extract medical information using Ollama LLM
    
    Supports:
    - medications: Extract steroid and Avastin status
    - radiation_date: Extract radiation completion date
    - suitable_prior: Check for prior imaging availability
    - imaging_assessment: Compare current vs prior imaging
    - on_medications: Determine medication effects on improvement
    - avastin_response: Analyze Avastin response type
    - steroid_effects: Analyze steroid effect timing
    - time_since_xrt: Apply 90-day radiation rule
    """
    try:
        if not request.clinical_note.strip():
            raise HTTPException(400, "Clinical note cannot be empty")
        
        # Use different model if specified
        if request.model != ollama_service.model:
            extraction_service = OllamaExtractionService(model=request.model)
        else:
            extraction_service = ollama_service
        
        # Route to appropriate extraction method
        if request.extraction_type == "medications":
            result = await extraction_service.extract_medications(request.clinical_note)
        elif request.extraction_type == "radiation_date":
            result = await extraction_service.extract_radiation_date(request.clinical_note)
        elif request.extraction_type in ["suitable_prior", "imaging_assessment", "on_medications", 
                                       "avastin_response", "steroid_effects", "time_since_xrt"]:
            # BT-RADS flowchart nodes
            result = await extraction_service.extract_btrads_node(
                request.clinical_note, 
                request.extraction_type,
                request.context_data
            )
        else:
            raise HTTPException(400, f"Invalid extraction type: {request.extraction_type}")
        
        return ExtractionResponse(**result)
        
    except Exception as e:
        logger.error(f"LLM extraction error: {e}")
        raise HTTPException(500, f"Extraction failed: {str(e)}")


@router.get("/models")
async def list_available_models():
    """List available Ollama models"""
    try:
        import ollama
        models = ollama.list()
        return {
            "models": [m["model"] for m in models["models"]],
            "default": "phi4:14b"
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return {
            "models": ["phi4:14b"],
            "default": "phi4:14b",
            "error": str(e)
        }


@router.get("/status")
async def check_ollama_status():
    """Check if Ollama service is running"""
    try:
        import ollama
        # Try to list models as a health check
        models = ollama.list()
        return {
            "status": "online",
            "available_models": len(models["models"]),
            "default_model": "phi4:14b"
        }
    except Exception as e:
        return {
            "status": "offline",
            "error": str(e),
            "message": "Please ensure Ollama is running locally on port 11434"
        }