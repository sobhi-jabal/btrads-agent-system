"""Agent management API routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any

from models.agent import AgentResult
from services.agent_service import AgentService

router = APIRouter()
agent_service = AgentService()

@router.get("/list")
async def list_available_agents():
    """List all available agents and their capabilities"""
    agents = [
        {
            "id": "prior_assessment_agent",
            "name": "Prior Assessment Agent",
            "node": "node_1_suitable_prior",
            "description": "Determines if suitable prior imaging is available for comparison",
            "extraction_type": "binary",
            "possible_values": ["yes", "no", "unknown"]
        },
        {
            "id": "imaging_comparison_agent",
            "name": "Imaging Comparison Agent",
            "node": "node_2_imaging_assessment",
            "description": "Compares current imaging with prior using volume data",
            "extraction_type": "categorical",
            "possible_values": ["improved", "unchanged", "worse", "unknown"]
        },
        {
            "id": "medication_status_agent",
            "name": "Medication Status Agent",
            "node": "medication_status",
            "description": "Extracts current steroid and Avastin status",
            "extraction_type": "complex",
            "fields": ["steroid_status", "avastin_status"]
        },
        {
            "id": "radiation_timeline_agent",
            "name": "Radiation Timeline Agent",
            "node": "radiation_timeline",
            "description": "Determines radiation completion date and calculates time since XRT",
            "extraction_type": "date",
            "output": "days_since_radiation"
        },
        {
            "id": "component_analysis_agent",
            "name": "Component Analysis Agent",
            "node": "node_5_what_is_worse",
            "description": "Analyzes which components (FLAIR/enhancement) are worse",
            "extraction_type": "categorical",
            "possible_values": ["flair_or_enh", "flair_and_enh", "unknown"]
        },
        {
            "id": "extent_analysis_agent",
            "name": "Extent Analysis Agent",
            "node": "node_6_how_much_worse",
            "description": "Applies 40% threshold rule for extent of worsening",
            "extraction_type": "categorical",
            "possible_values": ["minor", "major", "unknown"]
        },
        {
            "id": "progression_pattern_agent",
            "name": "Progression Pattern Agent",
            "node": "node_7_progressive",
            "description": "Determines if worsening is progressive over multiple studies",
            "extraction_type": "binary",
            "possible_values": ["yes", "no", "unknown"]
        }
    ]
    
    return {"agents": agents, "total": len(agents)}

@router.get("/results/{patient_id}")
async def get_agent_results(
    patient_id: str,
    agent_id: Optional[str] = None,
    node_id: Optional[str] = None,
    validation_status: Optional[str] = None
):
    """Get agent results for a patient with optional filtering"""
    try:
        results = await agent_service.get_results(
            patient_id=patient_id,
            agent_id=agent_id,
            node_id=node_id,
            validation_status=validation_status
        )
        return {
            "patient_id": patient_id,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(500, f"Error fetching results: {str(e)}")

@router.get("/result/{result_id}")
async def get_agent_result(result_id: int):
    """Get a specific agent result by ID"""
    result = await agent_service.get_result_by_id(result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    return result

@router.post("/test/{agent_id}")
async def test_agent(
    agent_id: str,
    test_data: Dict[str, Any]
):
    """Test an agent with sample data"""
    try:
        # Extract test parameters
        clinical_note = test_data.get("clinical_note", "")
        context = test_data.get("context", {})
        
        if not clinical_note:
            raise ValueError("clinical_note is required")
        
        # Run agent
        result = await agent_service.test_agent(
            agent_id=agent_id,
            clinical_note=clinical_note,
            context=context
        )
        
        return {
            "success": True,
            "result": result
        }
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Agent test failed: {str(e)}")

@router.get("/performance/{agent_id}")
async def get_agent_performance(
    agent_id: str,
    days: int = Query(7, description="Number of days to analyze")
):
    """Get performance metrics for an agent"""
    try:
        metrics = await agent_service.get_agent_performance(agent_id, days)
        return metrics
    except Exception as e:
        raise HTTPException(500, f"Error calculating metrics: {str(e)}")