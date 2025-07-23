"""Agent for analyzing extent of changes"""
from typing import Dict, Any
import logging
import time
from datetime import datetime

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class ExtentAnalysisAgent(SimpleBaseAgent):
    """Agent responsible for analyzing extent of changes (localized vs distant)"""
    
    def __init__(self):
        super().__init__(
            agent_id="extent-analysis",
            name="Extent Analysis Agent",
            description="Analyzes whether changes are localized or involve distant sites"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract extent analysis from clinical note"""
        start_time = time.time()
        try:
            # Create prompt for extent analysis
            prompt = f"""
            Analyze the extent of changes described in this clinical note.
            
            Clinical Note:
            {clinical_note}
            
            Task: Determine whether changes are localized or involve distant sites.
            Look for:
            - Mentions of multiple locations or sites
            - Words like "multifocal", "distant", "widespread", "disseminated"
            - Specific anatomical locations mentioned
            - Any indication of new lesions at distant sites
            
            A change is considered "distant" if:
            - New lesions appear at sites distant from the primary/original site
            - Multiple non-contiguous areas are involved
            - There's mention of disseminated or widespread disease
            
            Return JSON format:
            {{
                "is_localized": true/false,
                "has_distant_sites": true/false,
                "locations": ["list of anatomical locations mentioned"],
                "extent_description": "description of extent",
                "evidence_sentences": ["list of relevant sentences"],
                "confidence": 0.0-1.0,
                "reasoning": "brief explanation"
            }}
            """
            
            # Get LLM response
            response = await self._call_llm(prompt)
            
            # Determine extent category
            is_localized = response.get("is_localized", True)
            has_distant_sites = response.get("has_distant_sites", False)
            
            result_data = {
                "is_localized": is_localized,
                "has_distant_sites": has_distant_sites,
                "extent_category": "distant" if has_distant_sites else "localized",
                "locations": response.get("locations", []),
                "extent_description": response.get("extent_description", "")
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
                node_id="extent_analysis",
                timestamp=datetime.utcnow(),
                extracted_value=result_data,
                confidence=response.get("confidence", 0.75),
                reasoning=response.get("reasoning", ""),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="mock-llm"
            )
            
        except Exception as e:
            logger.error(f"Error in ExtentAnalysisAgent: {e}")
            return self._create_error_result(patient_id, str(e))