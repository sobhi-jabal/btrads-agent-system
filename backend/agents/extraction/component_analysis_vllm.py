"""
Component Analysis Agent using vLLM for real extraction
Determines which imaging components (FLAIR/enhancement) show worsening
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig
from utils.btrads_calculations import determine_component_worsening

logger = logging.getLogger(__name__)

class ComponentAnalysisAgent(VLLMBaseAgent):
    """Agent for analyzing which components are worse using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="component-analysis",
            name="Component Analysis Agent",
            description="Analyzes which imaging components show worsening when overall imaging is worse",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="high",
                require_json=True,
                confidence_threshold=0.75
            )
        )
        
        # Component-specific patterns
        self.flair_patterns = [
            r'(?i)FLAIR\s*(signal|hyperintensity|abnormality)',
            r'(?i)(T2|T2-weighted)\s*(signal|hyperintensity)',
            r'(?i)(edema|vasogenic\s*edema|peritumoral)',
            r'(?i)non-enhancing\s*(component|tumor|disease)',
        ]
        
        self.enhancement_patterns = [
            r'(?i)(enhancement|enhancing)',
            r'(?i)(contrast|gadolinium)\s*(enhancement|uptake)',
            r'(?i)post-contrast',
            r'(?i)(nodular|ring|rim)\s*enhancement',
        ]
        
        self.worsening_patterns = [
            r'(?i)(increas|worsen|progress|new|additional)',
            r'(?i)(larger|more\s*extensive|greater)',
            r'(?i)(develop|emerg|expand)',
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for component analysis"""
        return """You are an expert neuroradiologist specializing in brain tumor imaging components.
Your expertise includes:
- Distinguishing FLAIR signal abnormalities from enhancement
- Understanding tumor vs treatment-related changes
- Recognizing patterns of progression in different components
- Applying BT-RADS criteria for component analysis

When the overall imaging shows worsening, you must determine WHICH components are worse:
- FLAIR represents non-enhancing tumor/edema
- Enhancement represents blood-brain barrier disruption/active tumor
- Both can worsen independently or together

Key patterns:
- Treatment effect: Often FLAIR worsening without enhancement change
- True progression: Usually both components worsen
- Pseudoprogression: May show increased enhancement early after radiation"""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for component analysis"""
        
        # Add volume context if available
        volume_info = ""
        if context.get("flair_change_pct") is not None and context.get("enhancement_change_pct") is not None:
            flair_pct = context["flair_change_pct"]
            enh_pct = context["enhancement_change_pct"]
            volume_info = f"""
Volume measurements:
- FLAIR change: {flair_pct:+.1f}%
- Enhancement change: {enh_pct:+.1f}%"""
        
        return f"""Clinical Note:
{clinical_note}
{volume_info}

Given that the overall imaging shows WORSENING, determine which specific components are worse.

COMPONENT ANALYSIS:
- 'flair_or_enh': Either FLAIR OR enhancement is worse (but not both)
- 'flair_and_enh': BOTH FLAIR AND enhancement are worse
- 'unknown': Cannot determine which components are worse

IMPORTANT:
- This analysis assumes overall worsening is already established
- Look for specific mentions of FLAIR vs enhancement changes
- "New enhancement" always counts as enhancement worsening
- Consider volume data if no clear text description

Decision logic:
- If only FLAIR mentioned as worse → 'flair_or_enh'
- If only enhancement mentioned as worse → 'flair_or_enh'  
- If both mentioned as worse → 'flair_and_enh'
- If volumes show >10% increase in both → 'flair_and_enh'

Return JSON format:
{{
    "component_status": "flair_or_enh/flair_and_enh/unknown",
    "flair_worse": true/false,
    "enhancement_worse": true/false,
    "flair_description": "description of FLAIR changes if mentioned",
    "enhancement_description": "description of enhancement changes if mentioned",
    "new_enhancement": true/false,
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes about component changes"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for component analysis"""
        
        # First try calculation-based assessment if volume data available
        if (context.get("flair_change_pct") is not None and 
            context.get("enhancement_change_pct") is not None):
            
            component_status, reasoning = determine_component_worsening(
                context["flair_change_pct"],
                context["enhancement_change_pct"]
            )
            
            if component_status != "unknown":
                logger.info(f"Using calculation-based component analysis: {component_status}")
                logger.info(f"Reasoning: {reasoning}")
                return component_status, f"Calculated: {reasoning}", 0.95
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract component status
            status = data.get("component_status", "unknown").lower()
            
            # Validate and normalize
            if status not in ["flair_or_enh", "flair_and_enh", "unknown"]:
                status = "unknown"
            
            # Check individual components
            flair_worse = data.get("flair_worse", False)
            enh_worse = data.get("enhancement_worse", False)
            
            # Validate consistency
            if flair_worse and enh_worse and status != "flair_and_enh":
                logger.warning("Both components worse but status not 'flair_and_enh'")
                status = "flair_and_enh"
            elif (flair_worse or enh_worse) and not (flair_worse and enh_worse) and status != "flair_or_enh":
                logger.warning("Only one component worse but status not 'flair_or_enh'")
                status = "flair_or_enh"
            
            # Build reasoning
            reasoning_parts = []
            
            if flair_worse:
                desc = data.get("flair_description", "increased FLAIR signal")
                reasoning_parts.append(f"FLAIR worse: {desc[:50]}")
            
            if enh_worse:
                desc = data.get("enhancement_description", "increased enhancement")
                reasoning_parts.append(f"Enhancement worse: {desc[:50]}")
            
            if data.get("new_enhancement"):
                reasoning_parts.append("New enhancement present")
                status = "flair_and_enh" if flair_worse else "flair_or_enh"
                enh_worse = True
            
            # Try calculation if LLM couldn't determine
            if status == "unknown" and context.get("flair_change_pct") is not None:
                calc_status, calc_reasoning = determine_component_worsening(
                    context.get("flair_change_pct", 0),
                    context.get("enhancement_change_pct", 0)
                )
                if calc_status != "unknown":
                    status = calc_status
                    reasoning_parts.append(calc_reasoning)
                    confidence = 0.85  # Good confidence for calculation
            
            reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Component analysis performed"
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # Reduce confidence if relying on volumes alone
            if "volume" in reasoning.lower() and len(data.get("evidence", [])) == 0:
                confidence *= 0.8
            
            return status, reasoning, confidence
            
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
        
        # Check for both components
        flair_worse = any(word in response_lower for word in ["flair worse", "flair increased", "more flair"])
        enh_worse = any(word in response_lower for word in ["enhancement worse", "enhancement increased", "new enhancement"])
        
        if flair_worse and enh_worse:
            return "flair_and_enh", "Both components worse (pattern matching)", 0.5
        elif flair_worse or enh_worse:
            return "flair_or_enh", "One component worse (pattern matching)", 0.5
        else:
            # Try volume-based determination
            if (context.get("flair_change_pct") is not None and 
                context.get("enhancement_change_pct") is not None):
                status, reasoning = determine_component_worsening(
                    context["flair_change_pct"],
                    context["enhancement_change_pct"]
                )
                if status != "unknown":
                    return status, f"{reasoning} (fallback)", 0.6
            
            return "unknown", "Component changes unclear", 0.2
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate component analysis extraction"""
        
        # Validate format
        if extracted_value not in ["flair_or_enh", "flair_and_enh", "unknown"]:
            return False, f"Invalid component status: {extracted_value}"
        
        # Log volume context for debugging
        if context.get("flair_change_pct") is not None:
            flair_pct = context["flair_change_pct"]
            enh_pct = context.get("enhancement_change_pct", 0)
            logger.info(f"Volume context: FLAIR {flair_pct:+.1f}%, Enhancement {enh_pct:+.1f}%")
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for unclear components"""
        return "Review imaging to clarify which components (FLAIR vs enhancement) show worsening"