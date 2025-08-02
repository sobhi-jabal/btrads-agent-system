"""
Extent Analysis Agent using vLLM for real extraction
Applies 40% threshold rule to determine major vs minor worsening
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig
from utils.btrads_calculations import apply_40_percent_rule

logger = logging.getLogger(__name__)

class ExtentAnalysisAgent(VLLMBaseAgent):
    """Agent for analyzing extent of worsening using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="extent-analysis", 
            name="Extent Analysis Agent",
            description="Applies 40% threshold rule when both FLAIR and enhancement are worse",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="high",
                require_json=True,
                confidence_threshold=0.75
            )
        )
        
        # Patterns for extent descriptions
        self.major_patterns = [
            r'(?i)(significant|substantial|marked|extensive)\s*(increase|worsening|progression)',
            r'(?i)(large|major)\s*(increase|progression)',
            r'(?i)more\s*than\s*40%?\s*increase',
            r'(?i)>40%?\s*increase',
            r'(?i)(doubled|tripled|multifocal\s*progression)',
        ]
        
        self.minor_patterns = [
            r'(?i)(mild|minimal|slight|small)\s*(increase|worsening|progression)',
            r'(?i)(minor|modest)\s*(increase|progression)',
            r'(?i)less\s*than\s*40%?\s*increase',
            r'(?i)<40%?\s*increase',
            r'(?i)(subtle|equivocal)\s*change',
        ]
        
        self.percentage_patterns = [
            r'(?i)(\d+(?:\.\d+)?)\s*%?\s*increase',
            r'(?i)increased?\s*by\s*(\d+(?:\.\d+)?)\s*%',
            r'(?i)(\d+(?:\.\d+)?)\s*%?\s*(larger|bigger|worse)',
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for extent analysis"""
        return """You are an expert neuroradiologist applying BT-RADS extent criteria.
Your expertise includes:
- Quantifying tumor progression using volume measurements
- Applying the 40% threshold rule for BT-RADS classification
- Understanding RANO criteria for progression assessment
- Recognizing descriptive terms that indicate extent of change

The 40% THRESHOLD RULE (when both FLAIR and enhancement are worse):
- MAJOR worsening (≥40% increase) → BT-4 (highly suspicious)
- MINOR worsening (<40% increase) → Continue to progression pattern analysis

Key indicators of extent:
- Explicit percentage increases
- Descriptive terms (significant/marked vs mild/minimal)
- Volume measurements and calculations
- Radiologist's impression of extent

Remember: This rule only applies when BOTH components are worse."""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for extent analysis"""
        
        # Add volume context
        volume_info = ""
        max_increase = None
        if context.get("flair_change_pct") is not None and context.get("enhancement_change_pct") is not None:
            flair_pct = context["flair_change_pct"]
            enh_pct = context["enhancement_change_pct"]
            max_increase = max(flair_pct, enh_pct)
            volume_info = f"""
Volume measurements:
- FLAIR change: {flair_pct:+.1f}%
- Enhancement change: {enh_pct:+.1f}%
- Maximum increase: {max_increase:+.1f}%

NOTE: Apply 40% threshold to the LARGER of the two increases."""
        
        return f"""Clinical Note:
{clinical_note}
{volume_info}

Given that BOTH FLAIR and enhancement show worsening, apply the 40% threshold rule.

EXTENT CLASSIFICATION:
- 'major': Worsening ≥40% (leads to BT-4)
- 'minor': Worsening <40% (continue algorithm)
- 'unknown': Cannot determine extent of worsening

IMPORTANT:
- Look for percentage increases mentioned in the text
- Consider descriptive terms (significant/marked = likely major)
- Use volume measurements if no explicit percentages given
- The 40% threshold applies to the LARGER of the two component increases

Decision guidance:
- Explicit ≥40% increase → 'major'
- Terms like "significant", "marked", "extensive" → likely 'major'
- Terms like "mild", "minimal", "slight" → likely 'minor'
- Volume data showing ≥40% in either component → 'major'

Return JSON format:
{{
    "extent_classification": "major/minor/unknown",
    "percentage_increase": numeric value if determinable,
    "percentage_source": "text/volume/estimate",
    "descriptive_terms": ["terms used to describe extent"],
    "flair_increase": percentage if mentioned,
    "enhancement_increase": percentage if mentioned,
    "radiologist_assessment": "quote if they assess extent",
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes about extent of worsening"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for extent analysis"""
        
        # First try calculation-based assessment if volume data available
        if (context.get("flair_change_pct") is not None and 
            context.get("enhancement_change_pct") is not None):
            
            extent, reasoning = apply_40_percent_rule(
                context["flair_change_pct"],
                context["enhancement_change_pct"]
            )
            
            if extent != "unknown":
                logger.info(f"Using 40% rule calculation: {extent}")
                logger.info(f"Reasoning: {reasoning}")
                return extent, f"Rule-based: {reasoning}", 0.95
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract extent classification
            extent = data.get("extent_classification", "unknown").lower()
            
            # Validate and normalize
            if extent not in ["major", "minor", "unknown"]:
                extent = "unknown"
            
            # Get percentage if available
            percentage = data.get("percentage_increase")
            
            # Apply 40% rule if we have a percentage
            if percentage is not None and percentage != "unknown":
                try:
                    pct_value = float(percentage)
                    if pct_value >= 40 and extent != "major":
                        logger.warning(f"Percentage {pct_value}% indicates major but classified as {extent}")
                        extent = "major"
                    elif pct_value < 40 and pct_value > 0 and extent != "minor":
                        logger.warning(f"Percentage {pct_value}% indicates minor but classified as {extent}")
                        extent = "minor"
                except (ValueError, TypeError):
                    pass
            
            # Build reasoning
            reasoning_parts = []
            
            if extent == "major":
                reasoning_parts.append("Major worsening (≥40%)")
            elif extent == "minor":
                reasoning_parts.append("Minor worsening (<40%)")
            
            if percentage is not None:
                source = data.get("percentage_source", "unspecified")
                reasoning_parts.append(f"{percentage}% increase ({source})")
            
            # Add descriptive terms
            terms = data.get("descriptive_terms", [])
            if terms:
                reasoning_parts.append(f"Described as: {', '.join(terms[:2])}")
            
            # Try calculation if LLM couldn't determine
            if extent == "unknown" and context.get("flair_change_pct") is not None:
                calc_extent, calc_reasoning = apply_40_percent_rule(
                    context.get("flair_change_pct", 0),
                    context.get("enhancement_change_pct", 0)
                )
                if calc_extent != "unknown":
                    extent = calc_extent
                    reasoning_parts.append(calc_reasoning)
                    confidence = 0.9  # High confidence for calculation
            
            # Add evidence
            evidence = data.get("evidence", [])
            if evidence and len(evidence) > 0:
                reasoning_parts.append(f'"{evidence[0][:60]}..."')
            
            reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Extent analysis performed"
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # Boost confidence if we have explicit percentage
            if percentage is not None and data.get("percentage_source") == "text":
                confidence = min(confidence * 1.2, 1.0)
            
            return extent, reasoning, confidence
            
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
        
        # Look for percentage mentions
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', response_lower)
        if pct_match:
            pct_value = float(pct_match.group(1))
            if pct_value >= 40:
                return "major", f"{pct_value}% increase (pattern matching)", 0.6
            else:
                return "minor", f"{pct_value}% increase (pattern matching)", 0.6
        
        # Check descriptive terms
        if any(pattern in response_lower for pattern in ["significant", "marked", "extensive", "major"]):
            return "major", "Significant worsening described (pattern matching)", 0.5
        elif any(pattern in response_lower for pattern in ["mild", "minimal", "slight", "minor"]):
            return "minor", "Mild worsening described (pattern matching)", 0.5
        else:
            # Use volume data
            if (context.get("flair_change_pct") is not None and 
                context.get("enhancement_change_pct") is not None):
                extent, reasoning = apply_40_percent_rule(
                    context["flair_change_pct"],
                    context["enhancement_change_pct"]
                )
                if extent != "unknown":
                    return extent, f"{reasoning} (fallback)", 0.7
            
            return "unknown", "Extent of worsening unclear", 0.2
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate extent analysis extraction"""
        
        # Validate format
        if extracted_value not in ["major", "minor", "unknown"]:
            return False, f"Invalid extent classification: {extracted_value}"
        
        # Log and validate against volume context
        if (context.get("flair_change_pct") is not None and 
            context.get("enhancement_change_pct") is not None):
            
            calc_extent, calc_reasoning = apply_40_percent_rule(
                context["flair_change_pct"],
                context["enhancement_change_pct"]
            )
            
            logger.info(f"Calculation result: {calc_extent} - {calc_reasoning}")
            
            if calc_extent != "unknown" and calc_extent != extracted_value:
                logger.warning(f"Extracted '{extracted_value}' differs from calculated '{calc_extent}'")
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for unclear extent"""
        return "Request quantitative progression assessment or volume measurements from radiology"