"""Agent for extracting radiation timeline information"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import time

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class RadiationTimelineAgent(SimpleBaseAgent):
    """Agent responsible for extracting radiation timeline information"""
    
    def __init__(self):
        super().__init__(
            agent_id="radiation-timeline",
            name="Radiation Timeline Agent",
            description="Extracts radiation treatment dates and timelines"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract radiation timeline from clinical note"""
        start_time = time.time()
        try:
            # Use Ollama for extraction
            prompt = self._create_prompt(clinical_note)
            
            # Extract radiation information
            extracted_data = await self._call_llm(prompt)
            
            # Check if LLM call failed
            if extracted_data.get("error", False):
                # Set appropriate default values when LLM fails
                extracted_data = {
                    "radiation_date_str": None,
                    "radiation_type": None,
                    "radiation_location": None,
                    "evidence_sentences": [],
                    "confidence": 0.0,
                    "reasoning": "LLM extraction failed"
                }
                logger.warning(f"LLM extraction failed, using defaults: {extracted_data.get('message', 'Unknown error')}")
            
            # Parse radiation date if found
            radiation_date = None
            if extracted_data.get("radiation_date_str"):
                try:
                    radiation_date = datetime.fromisoformat(extracted_data["radiation_date_str"])
                except:
                    pass
            
            # Calculate time since radiation
            time_since_radiation = None
            if radiation_date and context.get("followup_date"):
                followup_date = context["followup_date"]
                if isinstance(followup_date, str):
                    followup_date = datetime.fromisoformat(followup_date)
                delta = followup_date - radiation_date
                time_since_radiation = delta.days
            
            # Determine if within 90-day window
            within_90_days = False
            if time_since_radiation is not None:
                within_90_days = time_since_radiation <= 90
            
            result_data = {
                "radiation_date": radiation_date.isoformat() if radiation_date else None,
                "time_since_radiation_days": time_since_radiation,
                "within_90_days": within_90_days,
                "radiation_type": extracted_data.get("radiation_type"),
                "radiation_location": extracted_data.get("radiation_location")
            }
            
            # Find source sentences
            source_highlights = await self._highlight_sources(
                clinical_note, 
                extracted_data.get("evidence_sentences", [])
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                agent_id=self.agent_id,
                patient_id=patient_id,
                node_id="radiation-timeline",
                timestamp=datetime.utcnow(),
                extracted_value=result_data,
                confidence=extracted_data.get("confidence", 0.7),
                reasoning=extracted_data.get("reasoning", ""),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="phi4:14b"
            )
            
        except Exception as e:
            logger.error(f"Error in RadiationTimelineAgent: {e}")
            return self._create_error_result(patient_id, str(e))
    
    def _create_prompt(self, clinical_note: str) -> str:
        """Create prompt for radiation timeline extraction"""
        return f"""
        Extract radiation treatment information from this clinical note.
        
        Clinical Note:
        {clinical_note}
        
        Task: Identify any mentions of radiation therapy, including:
        - Date of radiation treatment
        - Type of radiation (e.g., stereotactic radiosurgery, whole brain radiation)
        - Location/target of radiation
        
        Provide your response in JSON format:
        {{
            "radiation_date_str": "YYYY-MM-DD format if found",
            "radiation_type": "type of radiation if mentioned",
            "radiation_location": "treatment location if mentioned",
            "evidence_sentences": ["list of sentences containing radiation info"],
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }}
        """
    
    async def validate(self, result: AgentResult, feedback: Dict[str, Any]) -> AgentResult:
        """Validate radiation timeline extraction"""
        # Update result based on feedback
        if "radiation_date" in feedback:
            result.extracted_value["radiation_date"] = feedback["radiation_date"]
            
            # Recalculate time since radiation
            if feedback["radiation_date"] and result.context.get("followup_date"):
                radiation_date = datetime.fromisoformat(feedback["radiation_date"])
                followup_date = result.context["followup_date"]
                if isinstance(followup_date, str):
                    followup_date = datetime.fromisoformat(followup_date)
                delta = followup_date - radiation_date
                result.extracted_value["time_since_radiation_days"] = delta.days
                result.extracted_value["within_90_days"] = delta.days <= 90
        
        result.validation_status = "validated"
        result.validated_value = result.extracted_value
        result.validator_notes = feedback.get("notes", "")
        
        return result