"""
Imaging Comparison Agent using vLLM for real extraction
Compares current imaging with prior to determine overall assessment
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig
from utils.btrads_calculations import apply_enhancement_priority_rule

logger = logging.getLogger(__name__)

class ImagingComparisonAgent(VLLMBaseAgent):
    """Agent for comparing imaging studies using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="imaging-comparison",
            name="Imaging Comparison Agent",
            description="Compares current with prior imaging to determine overall change",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="high",
                require_json=True,
                confidence_threshold=0.75
            )
        )
        
        # Patterns for identifying changes
        self.improvement_patterns = [
            r'(?i)(improv|decreas|diminish|reduc|resolv|regress)',
            r'(?i)(smaller|less\s+enhancement|favorable)',
            r'(?i)(no\s+longer\s+seen|resolved)',
        ]
        
        self.worsening_patterns = [
            r'(?i)(worsen|increas|progress|enlarg|expand|new)',
            r'(?i)(larger|more\s+enhancement|greater)',
            r'(?i)(additional|developing|emerging)',
        ]
        
        self.stable_patterns = [
            r'(?i)(stable|unchanged|no\s+(?:significant\s+)?change)',
            r'(?i)(similar|comparable|persistent)',
            r'(?i)(essentially\s+unchanged)',
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for imaging comparison"""
        return """You are an expert neuroradiologist specializing in brain tumor follow-up imaging.
Your expertise includes:
- Comparing enhancement and FLAIR signal changes
- Assessing tumor response to treatment
- Recognizing treatment-related changes vs tumor progression
- Understanding volume-based assessments and RANO criteria

You must determine the OVERALL imaging assessment with high precision:
- Consider BOTH enhancement and FLAIR changes
- Apply the enhancement priority rule (enhancement changes take precedence in mixed patterns)
- Recognize subtle changes vs significant changes
- Account for measurement variability (±10% is typically stable)

Focus on the radiologist's overall impression and conclusion."""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for imaging comparison"""
        
        # Add volume context if available
        volume_info = ""
        if context.get("flair_change_pct") is not None and context.get("enhancement_change_pct") is not None:
            flair_pct = context["flair_change_pct"]
            enh_pct = context["enhancement_change_pct"]
            volume_info = f"""
Volume measurements provided:
- FLAIR change: {flair_pct:+.1f}%
- Enhancement change: {enh_pct:+.1f}%

Note: Consider ±10% as stable due to measurement variability."""
        
        return f"""Clinical Note:
{clinical_note}
{volume_info}

Determine the OVERALL imaging assessment compared to prior.

IMAGING ASSESSMENT:
- 'improved': Overall improvement (decreased tumor burden)
- 'unchanged': Stable/no significant change (within ±10% or per radiologist)
- 'worse': Overall worsening (increased tumor burden)
- 'unknown': Cannot determine from available information

IMPORTANT RULES:
1. Enhancement changes take priority over FLAIR in mixed patterns
2. Consider ±10% change as stable unless radiologist states otherwise
3. Look for the radiologist's overall impression/conclusion
4. "New enhancement" always means worse
5. Complete resolution of enhancement means improved

Return JSON format:
{{
    "overall_assessment": "improved/unchanged/worse/unknown",
    "flair_change": "improved/unchanged/worse/unknown",
    "enhancement_change": "improved/unchanged/worse/unknown",
    "new_lesions": true/false,
    "radiologist_impression": "quote the overall impression if available",
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes supporting the assessment"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for imaging comparison"""
        
        # First try volume-based assessment if data is available
        if (context.get("flair_change_pct") is not None and 
            context.get("enhancement_change_pct") is not None):
            
            # Get volume assessment using the proven function
            volume_assessment, volume_reasoning = apply_enhancement_priority_rule(
                context["flair_change_pct"],
                context["enhancement_change_pct"],
                context.get("baseline_flair"),
                context.get("baseline_enhancement"),
                context.get("followup_flair"),
                context.get("followup_enhancement")
            )
            
            if volume_assessment != "unknown":
                logger.info(f"Using volume-based assessment: {volume_assessment}")
                logger.info(f"Volume reasoning: {volume_reasoning}")
                # High confidence for volume-based assessment
                return volume_assessment, f"Volume-based: {volume_reasoning}", 0.95
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract overall assessment
            overall = data.get("overall_assessment", "unknown").lower()
            
            # Validate and normalize
            if overall not in ["improved", "unchanged", "worse", "unknown"]:
                overall = "unknown"
            
            # Apply enhancement priority rule if needed
            flair = data.get("flair_change", "unknown")
            enhancement = data.get("enhancement_change", "unknown")
            
            if overall == "unknown" and flair != "unknown" and enhancement != "unknown":
                # Apply enhancement priority rule
                if enhancement != "unchanged":
                    overall = enhancement
                else:
                    overall = flair
            
            # Build reasoning
            reasoning_parts = []
            
            if enhancement != "unknown":
                reasoning_parts.append(f"Enhancement: {enhancement}")
            if flair != "unknown":
                reasoning_parts.append(f"FLAIR: {flair}")
            
            if data.get("new_lesions"):
                reasoning_parts.append("New lesions present")
                overall = "worse"  # Override - new lesions always mean worse
            
            if data.get("radiologist_impression"):
                impression = data["radiologist_impression"][:100]
                reasoning_parts.append(f"Impression: \"{impression}...\"")
            
            # Add volume context if available
            if context.get("enhancement_change_pct") is not None:
                enh_pct = context["enhancement_change_pct"]
                if abs(enh_pct) > 10:
                    reasoning_parts.append(f"Volume: {enh_pct:+.1f}%")
            
            reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Imaging comparison extracted"
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # If we have volume data, validate and adjust confidence
            if (context.get("flair_change_pct") is not None and 
                context.get("enhancement_change_pct") is not None):
                # Compare with volume assessment
                volume_assessment, _ = apply_enhancement_priority_rule(
                    context["flair_change_pct"],
                    context["enhancement_change_pct"]
                )
                if volume_assessment == overall:
                    confidence = min(confidence * 1.2, 0.9)  # Boost for agreement
                else:
                    confidence *= 0.6  # Reduce for disagreement
                    logger.warning(f"LLM assessment '{overall}' disagrees with volume assessment '{volume_assessment}'")
            
            return overall, reasoning, confidence
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response}")
            # Fallback parsing
            return self._fallback_parse(response, context)
    
    def _validate_against_volumes(
        self,
        assessment: str,
        context: Dict[str, Any]
    ) -> bool:
        """Validate assessment against volume measurements"""
        
        flair_pct = context.get("flair_change_pct")
        enh_pct = context.get("enhancement_change_pct")
        
        if flair_pct is None or enh_pct is None:
            return True  # Can't validate without volumes
        
        # Use the proven volume assessment function
        volume_assessment, _ = apply_enhancement_priority_rule(flair_pct, enh_pct)
        return assessment == volume_assessment
    
    def _fallback_parse(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Fallback parsing if JSON fails"""
        
        response_lower = response.lower()
        
        # Check for clear indicators
        if any(pattern in response_lower for pattern in ["improved", "improvement", "decreased", "smaller"]):
            return "improved", "Imaging shows improvement (pattern matching)", 0.5
        elif any(pattern in response_lower for pattern in ["stable", "unchanged", "no change"]):
            return "unchanged", "Imaging stable (pattern matching)", 0.5
        elif any(pattern in response_lower for pattern in ["worse", "progression", "increased", "new"]):
            return "worse", "Imaging shows worsening (pattern matching)", 0.5
        else:
            # Try volume-based assessment
            if (context.get("flair_change_pct") is not None and 
                context.get("enhancement_change_pct") is not None):
                assessment, reasoning = apply_enhancement_priority_rule(
                    context["flair_change_pct"],
                    context["enhancement_change_pct"]
                )
                if assessment != "unknown":
                    return assessment, f"{reasoning} (fallback to volume)", 0.7
            
            return "unknown", "Unable to determine imaging change", 0.2
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate imaging comparison extraction"""
        
        # Validate format
        if extracted_value not in ["improved", "unchanged", "worse", "unknown"]:
            return False, f"Invalid assessment: {extracted_value}"
        
        # Warn about volume mismatch but don't fail
        if not self._validate_against_volumes(extracted_value, context):
            logger.warning("Assessment may not match volume data")
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for unclear imaging"""
        return "Request radiologist clarification on overall assessment or review images directly"