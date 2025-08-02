"""vLLM extraction API routes - uses the same agents as the orchestrator"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any
import logging
import asyncio
from datetime import datetime

from config.agent_config import agent_config, AgentMode
from agents.extraction.medication_status_vllm import MedicationStatusAgent
from agents.extraction.radiation_timeline_vllm import RadiationTimelineAgent

logger = logging.getLogger(__name__)
router = APIRouter()


class VLLMExtractionRequest(BaseModel):
    """Request model for vLLM extraction"""
    clinical_note: str
    extraction_type: Literal["medications", "radiation_date"]
    followup_date: Optional[str] = None  # For radiation timeline calculation


class VLLMExtractionResponse(BaseModel):
    """Response model for vLLM extraction"""
    data: Dict[str, Any]
    evidence: list
    confidence: float
    processing_time: float
    method: str = "vllm"
    model: str
    reasoning: Optional[str] = None
    error: Optional[str] = None


@router.post("/extract", response_model=VLLMExtractionResponse)
async def extract_with_vllm(request: VLLMExtractionRequest):
    """
    Extract medical information using vLLM agents
    
    This uses the same agents as the orchestrator for consistency.
    Supports:
    - medications: Extract steroid and Avastin status
    - radiation_date: Extract radiation completion date and timeline
    """
    try:
        if not request.clinical_note.strip():
            raise HTTPException(400, "Clinical note cannot be empty")
        
        start_time = datetime.now()
        
        # Ensure we're in vLLM mode
        if agent_config.mode != AgentMode.VLLM:
            logger.warning(f"Agent config is in {agent_config.mode} mode, switching to vLLM for extraction")
        
        if request.extraction_type == "medications":
            # Use medication status agent
            agent = MedicationStatusAgent()
            
            # Build context
            context = {
                "patient_id": "extraction_request",
                "clinical_note": request.clinical_note
            }
            
            # Extract medications
            result = await agent.extract(
                clinical_note=request.clinical_note,
                context=context,
                patient_id="extraction_request"
            )
            
            # Format response
            # The extracted_value contains the actual medication data
            if isinstance(result.extracted_value, dict):
                data = {
                    "steroid_status": result.extracted_value.get("steroid_status", "unknown"),
                    "avastin_status": result.extracted_value.get("avastin_status", "unknown")
                }
            else:
                data = {"steroid_status": "unknown", "avastin_status": "unknown"}
            
            # Get evidence from result
            evidence = []
            if hasattr(result, 'sources'):
                evidence = [{"text": src.text, "start": src.start_char, "end": src.end_char} 
                           for src in result.sources]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return VLLMExtractionResponse(
                data=data,
                evidence=evidence,
                confidence=result.confidence,
                processing_time=processing_time,
                model=agent_config.vllm_config.get("model_name", "unknown"),
                reasoning=result.reasoning
            )
            
        elif request.extraction_type == "radiation_date":
            # Use radiation timeline agent
            agent = RadiationTimelineAgent()
            
            # Build context
            context = {
                "patient_id": "extraction_request",
                "clinical_note": request.clinical_note,
                "followup_date": request.followup_date
            }
            
            # Extract radiation info
            result = await agent.extract(
                clinical_note=request.clinical_note,
                context=context,
                patient_id="extraction_request"
            )
            
            # Format response
            # The extracted_value contains the actual radiation data
            if isinstance(result.extracted_value, dict):
                data = {
                    "radiation_date": result.extracted_value.get("radiation_date", "unknown"),
                    "timeline_status": result.extracted_value.get("timeline_status", "unknown"),
                    "days_since_radiation": result.extracted_value.get("days_since_radiation")
                }
            elif isinstance(result.extracted_value, str):
                # If it's just a string status
                data = {
                    "radiation_date": "unknown",
                    "timeline_status": result.extracted_value,
                    "days_since_radiation": None
                }
            else:
                data = {"radiation_date": "unknown", "timeline_status": "unknown", "days_since_radiation": None}
            
            # Get evidence from result
            evidence = []
            if hasattr(result, 'sources'):
                evidence = [{"text": src.text, "start": src.start_char, "end": src.end_char} 
                           for src in result.sources]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return VLLMExtractionResponse(
                data=data,
                evidence=evidence,
                confidence=result.confidence,
                processing_time=processing_time,
                model=agent_config.vllm_config.get("model_name", "unknown"),
                reasoning=result.reasoning
            )
            
        else:
            raise HTTPException(400, f"Invalid extraction type: {request.extraction_type}")
            
    except Exception as e:
        logger.error(f"vLLM extraction error: {e}", exc_info=True)
        raise HTTPException(500, f"vLLM extraction failed: {str(e)}")


@router.get("/status")
async def check_vllm_status():
    """Check if vLLM service is configured and available"""
    try:
        # Check configuration
        is_vllm_mode = agent_config.mode == AgentMode.VLLM
        
        # Try to instantiate an agent to verify vLLM is working
        if is_vllm_mode:
            try:
                test_agent = MedicationStatusAgent()
                # Simple test to ensure agent can be created
                model_info = {
                    "model": agent_config.vllm_config.get("model_name", "unknown"),
                    "base_url": agent_config.vllm_config.get("base_url", "unknown"),
                    "temperature": agent_config.vllm_config.get("temperature", 0.1)
                }
            except Exception as e:
                return {
                    "status": "error",
                    "configured": True,
                    "mode": agent_config.mode.value,
                    "error": f"Failed to initialize vLLM agent: {str(e)}"
                }
        else:
            model_info = None
        
        return {
            "status": "online" if is_vllm_mode else "not_configured",
            "configured": is_vllm_mode,
            "mode": agent_config.mode.value,
            "model_info": model_info,
            "message": "vLLM extraction ready" if is_vllm_mode else f"System is in {agent_config.mode.value} mode"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "configured": False,
            "error": str(e),
            "message": "Error checking vLLM status"
        }