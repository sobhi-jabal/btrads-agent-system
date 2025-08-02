"""
Radiation Timeline Agent using vLLM for real extraction
Determines if patient is within 90 days of radiation therapy
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re
from datetime import datetime, timedelta

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig
from utils.btrads_calculations import calculate_days_between, determine_radiation_timing

logger = logging.getLogger(__name__)

class RadiationTimelineAgent(VLLMBaseAgent):
    """Agent for extracting radiation timeline using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="radiation-timeline",
            name="Radiation Timeline Agent",
            description="Determines time since radiation therapy for BT-RADS classification",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="medium",
                require_json=True,
                confidence_threshold=0.8
            )
        )
        
        # Patterns for radiation mentions
        self.radiation_patterns = [
            r'(?i)(radiation|RT|XRT|radiotherapy|irradiation)',
            r'(?i)(Gamma\s*Knife|GammaKnife|stereotactic\s*radiosurgery|SRS|SBRT)',
            r'(?i)(fractionated\s*radiation|whole\s*brain\s*radiation|WBRT)',
            r'(?i)(completed?\s*radiation|finished?\s*radiation)',
            r'(?i)(\d+)\s*(days?|weeks?|months?)\s*(since|after|post|from)\s*radiation',
            r'(?i)radiation\s*(\d+)\s*(days?|weeks?|months?)\s*ago',
        ]
        
        # Date patterns
        self.date_patterns = [
            r'(?i)radiation.*?on\s*(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(?i)radiation.*?(\d{1,2}-\d{1,2}-\d{2,4})',
            r'(?i)(\d{1,2}/\d{1,2}/\d{2,4}).*?radiation',
            r'(?i)completed.*?(\w+\s*\d{1,2},?\s*\d{4})',
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for radiation timeline extraction"""
        return """You are a radiation oncologist specializing in brain tumor treatment timelines.
Your expertise includes:
- Identifying radiation therapy completion dates
- Calculating time intervals since treatment
- Understanding different radiation modalities (SRS, WBRT, fractionated)
- Recognizing treatment-related changes vs progression timing

You must determine if the patient is within 90 days of radiation therapy completion.
This is critical for BT-RADS classification:
- Within 90 days → BT-3a (favor treatment effect)
- Beyond 90 days → Continue algorithm

Consider:
- Explicit radiation dates mentioned
- Time intervals stated (days/weeks/months since radiation)
- Treatment completion vs start dates
- Most recent radiation if multiple courses"""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for radiation timeline"""
        
        # Add context about scan date
        context_info = ""
        if context.get("followup_date"):
            context_info = f"\nCurrent scan date: {context['followup_date']}"
        if context.get("days_since_radiation") is not None:
            context_info += f"\nCalculated days since radiation: {context['days_since_radiation']} days"
        
        return f"""Clinical Note:
{clinical_note}
{context_info}

Determine if the patient is within 90 days of completing radiation therapy.

RADIATION TIMELINE:
- 'within_90_days': Patient completed radiation ≤90 days before current scan
- 'beyond_90_days': Patient completed radiation >90 days before current scan
- 'no_radiation': No history of radiation therapy mentioned
- 'unknown': Radiation mentioned but timeline unclear

IMPORTANT:
- Focus on COMPLETION date, not start date
- If multiple radiation courses, use the most recent
- Calculate from radiation completion to current scan date
- Be precise with day calculations when dates are available

Return JSON format:
{{
    "timeline_status": "within_90_days/beyond_90_days/no_radiation/unknown",
    "radiation_date": "completion date if available (YYYY-MM-DD format)",
    "radiation_type": "SRS/WBRT/fractionated/other if mentioned",
    "days_since_radiation": calculated number if determinable,
    "calculation_method": "explicit_date/time_phrase/context",
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes about radiation timing"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for radiation timeline"""
        
        # First check if we have days_since_radiation already calculated
        if context.get("days_since_radiation") is not None:
            days = context["days_since_radiation"]
            if days >= 0:
                timing, reasoning = determine_radiation_timing(days)
                logger.info(f"Using pre-calculated days: {days} -> {timing}")
                return timing, reasoning, 0.95  # High confidence for calculated values
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract timeline status
            timeline = data.get("timeline_status", "unknown").lower()
            
            # Validate and normalize
            valid_statuses = ["within_90_days", "beyond_90_days", "no_radiation", "unknown"]
            if timeline not in valid_statuses:
                timeline = "unknown"
            
            # Build reasoning
            reasoning_parts = []
            
            if timeline == "within_90_days":
                reasoning_parts.append("Recent radiation (<90 days)")
            elif timeline == "beyond_90_days":
                reasoning_parts.append("Remote radiation (>90 days)")
            elif timeline == "no_radiation":
                reasoning_parts.append("No radiation history")
            
            # Add specific timing if available
            if data.get("days_since_radiation") is not None:
                days = data["days_since_radiation"]
                reasoning_parts.append(f"{days} days post-RT")
                
                # Use function to determine timing
                timeline, _ = determine_radiation_timing(days)
            
            if data.get("radiation_date"):
                reasoning_parts.append(f"Completed {data['radiation_date']}")
            
            if data.get("radiation_type"):
                reasoning_parts.append(f"({data['radiation_type']})")
            
            # Add evidence
            evidence = data.get("evidence", [])
            if evidence and len(evidence) > 0:
                reasoning_parts.append(f'"{evidence[0][:80]}..."')
            
            reasoning = " - ".join(reasoning_parts) if reasoning_parts else "Radiation timeline assessed"
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # If we extracted a radiation date, calculate days and validate
            if data.get("radiation_date") and data["radiation_date"] != "unknown":
                if context.get("followup_date"):
                    calculated_days = calculate_days_between(
                        data["radiation_date"],
                        context["followup_date"]
                    )
                    if calculated_days >= 0:
                        # Override with calculated timing
                        timeline, reasoning = determine_radiation_timing(calculated_days)
                        confidence = 0.9  # High confidence for calculated
            
            return timeline, reasoning, confidence
            
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
        
        # Look for clear timeline indicators
        if "within 90 days" in response_lower or "recent radiation" in response_lower:
            return "within_90_days", "Recent radiation (pattern matching)", 0.5
        elif "beyond 90 days" in response_lower or "remote radiation" in response_lower:
            return "beyond_90_days", "Remote radiation (pattern matching)", 0.5
        elif "no radiation" in response_lower or "no history of radiation" in response_lower:
            return "no_radiation", "No radiation history (pattern matching)", 0.6
        else:
            # Try to extract days
            days_match = re.search(r'(\d+)\s*days?\s*(?:since|after|post)', response_lower)
            if days_match:
                days = int(days_match.group(1))
                if days <= 90:
                    return "within_90_days", f"{days} days post-radiation (pattern matching)", 0.5
                else:
                    return "beyond_90_days", f"{days} days post-radiation (pattern matching)", 0.5
            
            # Use context if available
            if context.get("days_since_radiation") is not None:
                days = context["days_since_radiation"]
                if days >= 0:
                    timing, reasoning = determine_radiation_timing(days)
                    return timing, f"{reasoning} (from context)", 0.6
            
            return "unknown", "Radiation timeline unclear", 0.2
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate radiation timeline extraction"""
        
        # Validate format
        valid_values = ["within_90_days", "beyond_90_days", "no_radiation", "unknown"]
        if extracted_value not in valid_values:
            return False, f"Invalid timeline status: {extracted_value}"
        
        # Cross-check with context if available
        if context.get("days_since_radiation") is not None:
            days = context["days_since_radiation"]
            if days <= 90 and extracted_value == "beyond_90_days":
                logger.warning(f"Context shows {days} days but extraction says beyond 90")
            elif days > 90 and extracted_value == "within_90_days":
                logger.warning(f"Context shows {days} days but extraction says within 90")
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for missing radiation info"""
        return "Review treatment history or radiation oncology records for radiation dates"