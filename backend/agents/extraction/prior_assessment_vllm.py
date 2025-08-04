"""
Prior Assessment Agent using vLLM for real extraction
Determines if suitable prior imaging is available for comparison
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re
from datetime import datetime

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig

logger = logging.getLogger(__name__)

class PriorAssessmentAgent(VLLMBaseAgent):
    """Agent for assessing prior imaging availability using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="prior-assessment",
            name="Prior Assessment Agent",
            description="Determines if suitable prior imaging is available for comparison",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="low",
                require_json=True,
                confidence_threshold=0.8
            )
        )
        
        # Patterns for identifying prior imaging mentions
        self.prior_patterns = [
            r'(?i)(prior|previous|earlier|comparison|baseline)\s*(MRI|MR|scan|imaging|study)',
            r'(?i)compared?\s*(to|with)\s*(prior|previous|earlier)',
            r'(?i)(interval|since|from)\s*(change|progression|improvement|stable)',
            r'(?i)no\s*(prior|previous|comparison)\s*(imaging|study|scan)',
            r'(?i)first\s*(?:time\s*)?(MRI|scan|study)',
            r'(?i)baseline\s*(examination|study|scan|MRI)'
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for prior assessment"""
        return """You are a neuroradiologist specializing in brain tumor imaging interpretation.
Your expertise includes:
- Determining availability and suitability of prior imaging for comparison
- Assessing imaging quality and protocol adequacy
- Identifying baseline vs follow-up studies
- Understanding BT-RADS reporting requirements

You must determine if suitable prior imaging is available for comparison with high accuracy.
Consider:
- Explicit mentions of prior/previous imaging
- Comparison statements in the report
- Baseline vs follow-up status
- Technical adequacy for comparison
- Time intervals between studies"""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for prior assessment"""
        
        # Add context about scan dates if available
        context_info = ""
        if context.get("baseline_date"):
            context_info = f"\nBaseline scan date: {context['baseline_date']}"
        if context.get("followup_date"):
            context_info += f"\nCurrent scan date: {context['followup_date']}"
        
        return f"""Clinical Note:
{clinical_note}
{context_info}

Determine if suitable prior imaging is available for comparison.

PRIOR IMAGING STATUS:
- 'yes': Suitable prior imaging is available and being compared
- 'no': No prior imaging available (first scan, no baseline, etc.)
- 'unknown': Cannot determine from available information

Consider:
1. Explicit mentions of comparison with prior imaging
2. References to baseline or previous studies
3. Interval change descriptions (implies prior available)
4. Statements about "first MRI" or "no prior imaging"
5. Technical adequacy mentions

Return JSON format:
{{
    "prior_available": "yes/no/unknown",
    "prior_date": "date if mentioned",
    "prior_type": "MRI type if specified (e.g., brain MRI with contrast)",
    "comparison_quality": "adequate/limited/not_mentioned",
    "reasoning": "brief explanation of determination",
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes from the note supporting your assessment"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for prior assessment"""
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract prior status
            prior_status = data.get("prior_available", "unknown").lower()
            
            # Validate and normalize
            if prior_status not in ["yes", "no", "unknown"]:
                prior_status = "unknown"
            
            # Build reasoning
            reasoning_parts = []
            if prior_status == "yes":
                reasoning_parts.append("Prior imaging available for comparison")
                if data.get("prior_date"):
                    reasoning_parts.append(f"Prior from {data['prior_date']}")
                if data.get("comparison_quality") == "limited":
                    reasoning_parts.append("(limited comparison)")
            elif prior_status == "no":
                reasoning_parts.append("No prior imaging available")
                reasoning_parts.append(data.get("reasoning", "First study or no baseline"))
            else:
                reasoning_parts.append("Prior imaging status unclear")
            
            # Add evidence if available
            evidence = data.get("evidence", [])
            if evidence and len(evidence) > 0:
                reasoning_parts.append(f"Based on: \"{evidence[0][:100]}...\"")
            
            reasoning = " - ".join(reasoning_parts)
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # Adjust confidence if unknown
            if prior_status == "unknown":
                confidence *= 0.7
            
            return prior_status, reasoning, confidence
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response}")
            # Fallback parsing
            return self._fallback_parse(response, context)
    
    def _fallback_parse(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Fallback parsing if JSON fails"""
        
        response_lower = response.lower()
        
        # Check for clear indicators
        if "no prior" in response_lower or "first scan" in response_lower or "baseline" in response_lower:
            return "no", "No prior imaging identified (pattern matching)", 0.6
        elif "compared to prior" in response_lower or "comparison with previous" in response_lower:
            return "yes", "Prior imaging available (pattern matching)", 0.6
        elif "interval change" in response_lower or "since prior" in response_lower:
            return "yes", "Prior imaging implied by interval change (pattern matching)", 0.5
        else:
            return "unknown", "Prior imaging status unclear (pattern matching)", 0.3
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate prior assessment extraction"""
        
        # Validate format
        if extracted_value not in ["yes", "no", "unknown"]:
            return False, f"Invalid prior status: {extracted_value}"
        
        # Cross-check with context if available
        if context.get("baseline_date") and context.get("followup_date"):
            # If we have both dates, there should be a prior
            if extracted_value == "no":
                logger.warning("Context suggests prior exists but extraction says 'no'")
                # Don't fail validation, but log the discrepancy
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for missing prior info"""
        return "Review imaging history in PACS or request prior study information"