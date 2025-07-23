"""Agent for imaging comparison assessment (Node 2)"""
from typing import Dict, Any
import logging
import time
from datetime import datetime

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class ImagingComparisonAgent(SimpleBaseAgent):
    """Agent for comparing current imaging with prior (improved/unchanged/worse)"""
    
    def __init__(self):
        super().__init__(
            agent_id="imaging-comparison",
            name="Imaging Comparison Agent",
            description="Compares current imaging with prior to determine if improved, unchanged, or worse"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract imaging comparison from clinical note"""
        start_time = time.time()
        try:
            # Get volume data from context
            flair_change_pct = context.get("flair_change_pct", 0)
            enhancement_change_pct = context.get("enhancement_change_pct", 0)
            baseline_date = context.get("baseline_date", "unknown")
            followup_date = context.get("followup_date", "unknown")
            
            # Create prompt for imaging comparison
            prompt = f"""
            You are a neuroradiology expert applying BT-RADS imaging assessment criteria using quantitative volume data.
            Your task is to compare current imaging with prior using both volume measurements and clinical descriptions.
            
            Clinical Note:
            {clinical_note}
            
            VOLUME DATA:
            - Baseline imaging: {baseline_date}
            - Follow-up imaging: {followup_date}
            - FLAIR volume change: {flair_change_pct}%
            - Enhancement volume change: {enhancement_change_pct}%
            
            CRITICAL RULES:
            1. NEGATIVE percentage = DECREASED volume = IMPROVEMENT
            2. POSITIVE percentage = INCREASED volume = WORSENING  
            3. Values between -10% and +10% = STABLE/UNCHANGED
            4. ENHANCEMENT PRIORITY: When FLAIR and enhancement change in opposite directions, prioritize enhancement
            
            DECISION LOGIC:
            - Both decreased (negative %) -> "improved"
            - Both stable (±10%) -> "unchanged" 
            - Either shows significant increase (>10%) -> "worse"
            - Mixed pattern -> Follow enhancement direction
            
            Return JSON format:
            {{
                "assessment": "improved/unchanged/worse/unknown",
                "reasoning": "explanation including volume analysis",
                "confidence": 0.0-1.0,
                "volume_pattern": "both_decreased/both_stable/both_increased/mixed",
                "enhancement_priority_applied": true/false,
                "evidence_sentences": ["relevant quotes"]
            }}
            """
            
            # Get LLM response
            response = await self._call_llm(prompt)
            
            # Extract the assessment
            assessment = response.get("assessment", "unknown")
            
            # Validate against volume data
            if assessment != "unknown" and flair_change_pct is not None and enhancement_change_pct is not None:
                flair_val = float(flair_change_pct)
                enh_val = float(enhancement_change_pct)
                
                # Check for mixed pattern
                flair_dir = "up" if flair_val > 10 else ("down" if flair_val < -10 else "stable")
                enh_dir = "up" if enh_val > 10 else ("down" if enh_val < -10 else "stable")
                
                if flair_dir != enh_dir and flair_dir != "stable" and enh_dir != "stable":
                    # Mixed pattern - enhancement priority
                    assessment = "worse" if enh_dir == "up" else "improved"
                    response["enhancement_priority_applied"] = True
            
            # Find source highlights
            source_highlights = await self._highlight_sources(
                clinical_note,
                response.get("evidence_sentences", [])
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                agent_id=self.agent_id,
                patient_id=patient_id,
                node_id="node_2_imaging_assessment",
                timestamp=datetime.utcnow(),
                extracted_value=assessment,
                confidence=response.get("confidence", 0.7),
                reasoning=response.get("reasoning", ""),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="mock-llm",
                metadata={
                    "volume_pattern": response.get("volume_pattern", "unknown"),
                    "enhancement_priority_applied": response.get("enhancement_priority_applied", False),
                    "flair_change_pct": flair_change_pct,
                    "enhancement_change_pct": enhancement_change_pct
                }
            )
            
        except Exception as e:
            logger.error(f"Error in ImagingComparisonAgent: {e}")
            return self._create_error_result(patient_id, str(e))