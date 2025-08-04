"""
Progression Pattern Agent using vLLM for real extraction
Determines if there's progressive worsening over multiple studies
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig

logger = logging.getLogger(__name__)

class ProgressionPatternAgent(VLLMBaseAgent):
    """Agent for analyzing progression patterns using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="progression-pattern",
            name="Progression Pattern Agent",
            description="Analyzes if there's progressive worsening over multiple imaging studies",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="high",
                require_json=True,
                confidence_threshold=0.75
            )
        )
        
        # Patterns for progression
        self.progression_patterns = [
            r'(?i)(progressive|progressing|continued?\s*progression)',
            r'(?i)(steady|gradual|slow)\s*(progression|worsening|increase)',
            r'(?i)(multiple|serial|consecutive)\s*studies?\s*show\w*\s*(worsen|progress)',
            r'(?i)worsen\w*\s*(over|across|through)\s*(multiple|several|serial)',
            r'(?i)(trend|pattern)\s*of\s*(progression|worsening)',
        ]
        
        self.stable_patterns = [
            r'(?i)(stable|unchanged)\s*(over|across|through)\s*(multiple|serial)',
            r'(?i)no\s*(progressive|continued)\s*(change|worsening)',
            r'(?i)(fluctuat|wax\w*\s*and\s*wan)',
            r'(?i)first\s*time\s*(worsen|progress)',
        ]
        
        self.temporal_patterns = [
            r'(?i)compared?\s*to\s*(multiple|several)\s*prior',
            r'(?i)over\s*the\s*(past|last)\s*(\d+)\s*(months?|scans?)',
            r'(?i)since\s*(\d{4}|\d+\s*months?\s*ago)',
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for progression pattern analysis"""
        return """You are an expert neuro-oncologist analyzing longitudinal imaging patterns.
Your expertise includes:
- Identifying trends across multiple imaging studies
- Distinguishing progressive disease from fluctuating changes
- Understanding tumor growth patterns over time
- Recognizing stable vs progressive minor changes

PROGRESSION PATTERN ANALYSIS (for minor worsening <40%):
- YES (progressive) → BT-4: Consistent worsening trend over multiple studies
- NO (not progressive) → BT-3c: First-time worsening or fluctuating changes

Key indicators of PROGRESSIVE pattern:
- Worsening on 2+ consecutive studies
- Steady increase over time (even if each change is small)
- Upward trend in measurements
- Described as "progressive" or "continued progression"

Key indicators of NON-PROGRESSIVE pattern:
- First instance of worsening after stability
- Fluctuating changes (improvement then worsening)
- Isolated worsening without prior trend
- Mixed changes across different areas"""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for progression pattern"""
        
        # Add temporal context
        context_info = ""
        if context.get("baseline_date") and context.get("followup_date"):
            context_info = f"""
Imaging timeline:
- Baseline: {context['baseline_date']}
- Current: {context['followup_date']}"""
        
        return f"""Clinical Note:
{clinical_note}
{context_info}

Given MINOR worsening (<40%), determine if there's a PROGRESSIVE pattern over multiple studies.

PROGRESSION PATTERN:
- 'yes': Progressive worsening over multiple studies (→ BT-4)
- 'no': No progressive pattern; first-time or fluctuating change (→ BT-3c)
- 'unknown': Cannot determine progression pattern

IMPORTANT CRITERIA:
1. Look for mentions of prior studies (not just the immediate prior)
2. Identify trends: "progressive", "continued worsening", "steady increase"
3. Consider number of studies showing worsening (≥2 consecutive = progressive)
4. First-time worsening after stability = NOT progressive
5. Fluctuating changes = NOT progressive

Examples:
- "Progressive enhancement over last 3 studies" → YES
- "Stable for 2 years, now shows mild worsening" → NO
- "Continued slow progression since 2023" → YES
- "Worsening compared to prior, but improved from 2 studies ago" → NO

Return JSON format:
{{
    "progression_pattern": "yes/no/unknown",
    "number_of_studies": count if mentioned,
    "time_period": "duration if mentioned (e.g., '6 months', '3 studies')",
    "pattern_description": "progressive/stable_then_worse/fluctuating/first_time",
    "trend_keywords": ["keywords indicating trend"],
    "prior_comparisons": ["mentions of comparisons to multiple priors"],
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes about progression pattern"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for progression pattern"""
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract progression pattern
            pattern = data.get("progression_pattern", "unknown").lower()
            
            # Validate and normalize
            if pattern not in ["yes", "no", "unknown"]:
                pattern = "unknown"
            
            # Build reasoning
            reasoning_parts = []
            
            if pattern == "yes":
                reasoning_parts.append("Progressive pattern identified")
            elif pattern == "no":
                reasoning_parts.append("No progressive pattern")
            
            # Add pattern description
            pattern_desc = data.get("pattern_description", "")
            if pattern_desc:
                if pattern_desc == "progressive":
                    reasoning_parts.append("Continued progression")
                elif pattern_desc == "stable_then_worse":
                    reasoning_parts.append("First worsening after stability")
                elif pattern_desc == "fluctuating":
                    reasoning_parts.append("Fluctuating changes")
                elif pattern_desc == "first_time":
                    reasoning_parts.append("First-time worsening")
            
            # Add temporal information
            if data.get("number_of_studies"):
                reasoning_parts.append(f"Over {data['number_of_studies']} studies")
            elif data.get("time_period"):
                reasoning_parts.append(f"Over {data['time_period']}")
            
            # Add trend keywords
            keywords = data.get("trend_keywords", [])
            if keywords:
                reasoning_parts.append(f"Key terms: {', '.join(keywords[:2])}")
            
            # Add evidence
            evidence = data.get("evidence", [])
            if evidence and len(evidence) > 0:
                reasoning_parts.append(f'"{evidence[0][:80]}..."')
            
            reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Progression pattern analyzed"
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # Adjust confidence based on evidence strength
            if pattern != "unknown":
                if data.get("number_of_studies") or data.get("time_period"):
                    confidence = min(confidence * 1.1, 1.0)
                if len(keywords) > 0:
                    confidence = min(confidence * 1.05, 1.0)
            
            return pattern, reasoning, confidence
            
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
        
        # Check for clear progression indicators
        progression_found = any(re.search(pattern, response_lower) for pattern in self.progression_patterns)
        stable_found = any(re.search(pattern, response_lower) for pattern in self.stable_patterns)
        
        if progression_found and not stable_found:
            return "yes", "Progressive pattern detected (pattern matching)", 0.5
        elif stable_found and not progression_found:
            return "no", "No progressive pattern (pattern matching)", 0.5
        elif "first" in response_lower and "worsen" in response_lower:
            return "no", "First-time worsening (pattern matching)", 0.6
        elif "multiple" in response_lower or "serial" in response_lower:
            if "worsen" in response_lower or "progress" in response_lower:
                return "yes", "Multiple studies show worsening (pattern matching)", 0.5
        
        return "unknown", "Progression pattern unclear", 0.2
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate progression pattern extraction"""
        
        # Validate format
        if extracted_value not in ["yes", "no", "unknown"]:
            return False, f"Invalid progression pattern: {extracted_value}"
        
        # Log context for debugging
        logger.info(f"Progression pattern determined: {extracted_value}")
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for unclear progression"""
        return "Review prior imaging reports to establish progression timeline and pattern"