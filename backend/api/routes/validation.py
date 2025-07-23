"""Validation API routes"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from models.agent import AgentValidationRequest
from services.validation_service import ValidationService

router = APIRouter()
validation_service = ValidationService()

@router.post("/validate")
async def validate_agent_result(request: AgentValidationRequest):
    """Validate an agent extraction result"""
    try:
        result = await validation_service.validate_result(
            patient_id=request.patient_id,
            validation_id=request.validation_id,
            validated_value=request.validated_value,
            notes=request.notes,
            validator_id=request.validator_id
        )
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Validation error: {str(e)}")

@router.post("/override/{patient_id}/{node_id}")
async def override_decision(
    patient_id: str,
    node_id: str,
    override_data: Dict[str, Any]
):
    """Override a decision at a specific node"""
    try:
        result = await validation_service.override_decision(
            patient_id=patient_id,
            node_id=node_id,
            new_value=override_data["value"],
            reason=override_data.get("reason"),
            override_by=override_data["override_by"]
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Override error: {str(e)}")

@router.get("/pending/{patient_id}")
async def get_pending_validations(patient_id: str):
    """Get all pending validations for a patient"""
    pending = await validation_service.get_pending_validations(patient_id)
    return {"patient_id": patient_id, "pending_validations": pending}