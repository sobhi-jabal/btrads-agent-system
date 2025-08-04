"""Agent for analyzing imaging components"""
from typing import Dict, Any
import logging
import time
from datetime import datetime

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class ComponentAnalysisAgent(SimpleBaseAgent):
    """Agent responsible for analyzing enhancement and FLAIR components"""
    
    def __init__(self):
        super().__init__(
            agent_id="component-analysis",
            name="Component Analysis Agent",
            description="Analyzes enhancement and FLAIR components for changes"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract component analysis from clinical note"""
        start_time = time.time()
        try:
            # Get change data from context
            flair_change = context.get("flair_change_percentage", 0)
            enhancement_change = context.get("enhancement_change_percentage", 0)
            
            # Create prompt for component analysis
            prompt = f"""
            Analyze the imaging component changes described in this clinical note.
            
            Clinical Note:
            {clinical_note}
            
            Known measurements:
            - FLAIR change: {flair_change:.1f}%
            - Enhancement change: {enhancement_change:.1f}%
            
            Task: Extract descriptions of how the FLAIR and enhancement components changed.
            Look for:
            - Descriptions of FLAIR signal changes
            - Descriptions of enhancement patterns
            - Any mentions of which component is dominant
            - Qualitative assessments of changes
            
            Return JSON format:
            {{
                "component_description": "description of component changes",
                "flair_description": "specific FLAIR changes if mentioned",
                "enhancement_description": "specific enhancement changes if mentioned",
                "evidence_sentences": ["list of relevant sentences"],
                "confidence": 0.0-1.0,
                "reasoning": "brief explanation"
            }}
            """
            
            # Get LLM response
            response = await self._call_llm(prompt, output_format="json")
            
            # Determine component behavior
            flair_increased = flair_change > 0
            enhancement_increased = enhancement_change > 0
            
            # Check for opposite direction changes (enhancement priority rule)
            opposite_direction = (flair_increased and not enhancement_increased) or \
                               (not flair_increased and enhancement_increased)
            
            result_data = {
                "flair_change": flair_change,
                "enhancement_change": enhancement_change,
                "flair_increased": flair_increased,
                "enhancement_increased": enhancement_increased,
                "opposite_direction": opposite_direction,
                "dominant_component": "enhancement" if opposite_direction else "both",
                "component_description": response.get("component_description", ""),
                "flair_description": response.get("flair_description", ""),
                "enhancement_description": response.get("enhancement_description", "")
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
                node_id="component_analysis",
                timestamp=datetime.utcnow(),
                extracted_value=result_data,
                confidence=response.get("confidence", 0.8),
                reasoning=response.get("reasoning", ""),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="phi4:14b"
            )
            
        except Exception as e:
            logger.error(f"Error in ComponentAnalysisAgent: {e}")
            return self._create_error_result(patient_id, str(e))