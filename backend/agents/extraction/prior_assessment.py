"""Agent for assessing suitable prior availability (Node 1)"""
from typing import Dict, Any
import logging
import time
from datetime import datetime

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class PriorAssessmentAgent(SimpleBaseAgent):
    """Agent for determining if suitable prior imaging is available"""
    
    def __init__(self):
        super().__init__(
            agent_id="prior-assessment",
            name="Prior Assessment Agent",
            description="Determines if suitable prior imaging is available for comparison"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract prior imaging availability from clinical note"""
        start_time = time.time()
        try:
            # Create prompt for prior assessment
            prompt = f"""
            Analyze this clinical note to determine if there is suitable prior imaging for BT-RADS comparison.
            
            Clinical Note:
            {clinical_note}
            
            Look for:
            - References to prior MRI scans
            - Comparison statements
            - Baseline post-operative imaging
            - Previous follow-up studies
            
            Return JSON format:
            {{
                "has_prior": true/false,
                "confidence": 0.0-1.0,
                "reasoning": "explanation",
                "evidence_sentences": ["relevant quotes"]
            }}
            """
            
            # Get LLM response
            response = await self._call_llm(prompt)
            
            # Extract the value
            has_prior = response.get("has_prior", False)
            
            # Find source highlights
            source_highlights = await self._highlight_sources(
                clinical_note,
                response.get("evidence_sentences", [])
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                agent_id=self.agent_id,
                patient_id=patient_id,
                node_id="node_1_suitable_prior",
                timestamp=datetime.utcnow(),
                extracted_value="yes" if has_prior else "no",
                confidence=response.get("confidence", 0.7),
                reasoning=response.get("reasoning", ""),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="mock-llm"
            )
            
        except Exception as e:
            logger.error(f"Error in PriorAssessmentAgent: {e}")
            return self._create_error_result(patient_id, str(e))