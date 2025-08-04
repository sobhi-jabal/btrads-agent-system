"""Agent for analyzing progression patterns"""
from typing import Dict, Any
import logging
import time
from datetime import datetime

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class ProgressionPatternAgent(SimpleBaseAgent):
    """Agent responsible for analyzing progression patterns"""
    
    def __init__(self):
        super().__init__(
            agent_id="progression-pattern",
            name="Progression Pattern Agent",
            description="Analyzes patterns of tumor progression"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract progression pattern from clinical note"""
        start_time = time.time()
        try:
            # Create prompt for progression pattern analysis
            prompt = f"""
            Analyze the progression pattern described in this clinical note.
            
            Clinical Note:
            {clinical_note}
            
            Task: Identify the pattern of tumor progression.
            Look for:
            - Infiltrative patterns (spreading along white matter tracts)
            - Expansive/mass-like growth
            - CSF dissemination or leptomeningeal involvement
            - Subependymal spread
            - Descriptions of how the tumor is growing or spreading
            
            Common patterns include:
            - Infiltrative: spreading along white matter, poorly defined margins
            - Expansive: well-defined mass effect, pushing boundaries
            - Mixed: combination of patterns
            - CSF dissemination: spread through cerebrospinal fluid spaces
            
            Return JSON format:
            {{
                "pattern_type": "infiltrative|expansive|mixed|csf_dissemination|unknown",
                "pattern_description": "description of the pattern",
                "progression_features": ["list of specific features mentioned"],
                "is_infiltrative": true/false,
                "is_expansive": true/false,
                "involves_csf": true/false,
                "evidence_sentences": ["list of relevant sentences"],
                "confidence": 0.0-1.0,
                "reasoning": "brief explanation"
            }}
            """
            
            # Get LLM response
            response = await self._call_llm(prompt, output_format="json")
            
            # Determine pattern type
            pattern_type = response.get("pattern_type", "unknown")
            
            result_data = {
                "pattern_type": pattern_type,
                "pattern_description": response.get("pattern_description", ""),
                "progression_features": response.get("progression_features", []),
                "is_infiltrative": response.get("is_infiltrative", False),
                "is_expansive": response.get("is_expansive", False),
                "involves_csf": response.get("involves_csf", False)
            }
            
            # Find source highlights
            source_highlights = await self._highlight_sources(
                clinical_note, 
                response.get("evidence_sentences", [])
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                agent_id=self.agent_id,
                patient_id=patient_id,
                node_id="progression_pattern",
                timestamp=datetime.utcnow(),
                extracted_value=result_data,
                confidence=response.get("confidence", 0.7),
                reasoning=response.get("reasoning", ""),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="phi4:14b"
            )
            
        except Exception as e:
            logger.error(f"Error in ProgressionPatternAgent: {e}")
            return self._create_error_result(patient_id, str(e))