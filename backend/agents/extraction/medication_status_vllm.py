"""
Medication Status Agent using vLLM for real extraction
Extracts current steroid and Avastin medication status
"""
from typing import Dict, Any, Tuple, Optional
import logging
import json
import re

from agents.base_vllm import VLLMBaseAgent, ExtractionConfig

logger = logging.getLogger(__name__)

class MedicationStatusAgent(VLLMBaseAgent):
    """Agent for extracting current medication status using vLLM"""
    
    def __init__(self):
        super().__init__(
            agent_id="medication-status",
            name="Medication Status Agent",
            description="Extracts current steroid and Avastin medication status from clinical notes",
            extraction_config=ExtractionConfig(
                task_type="medical_analysis",
                complexity="medium",
                require_json=True,
                confidence_threshold=0.7
            )
        )
        
        # Medication patterns for validation
        self.steroid_patterns = [
            r'(?i)(dexamethasone|decadron|prednis\w+|methylprednisolone|hydrocortisone)',
            r'(?i)(steroid|corticosteroid)',
        ]
        
        self.avastin_patterns = [
            r'(?i)(avastin|bevacizumab|BV)',
            r'(?i)(anti-?angiogenic|antiangiogenic)',
        ]
    
    def get_system_prompt(self) -> str:
        """System prompt for medication extraction"""
        return """You are a neuro-oncology pharmacist specializing in brain tumor treatments.
Your expertise includes:
- Corticosteroid management (dexamethasone, prednisone, etc.)
- Anti-angiogenic therapy (Avastin/bevacizumab)
- Medication dosing and tapering schedules
- Treatment side effects and interactions

You must extract CURRENT medication status with high precision, distinguishing between:
- Stable doses vs. changes (increases/decreases)
- New medications vs. ongoing therapy
- First-time treatments vs. continued therapy
- Completed/discontinued medications

Focus on the most recent medication information in the clinical note."""
    
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build extraction prompt for medications"""
        
        # Add context about scan dates if available
        context_info = ""
        if context.get("followup_date"):
            context_info = f"\nCurrent scan date: {context['followup_date']}"
        if context.get("baseline_date"):
            context_info += f"\nPrevious scan date: {context['baseline_date']}"
        
        return f"""Clinical Note:
{clinical_note}
{context_info}

Extract the CURRENT medication status as of the most recent visit/scan.

STEROID STATUS:
- 'none': Patient is not currently on steroids
- 'stable': Patient continues on same steroid dose
- 'increasing': Steroid dose being increased/escalated
- 'decreasing': Steroid dose being tapered/decreased  
- 'started': Patient newly started on steroids
- 'unknown': Cannot determine from available information

AVASTIN STATUS:
- 'none': Patient is not on Avastin therapy
- 'ongoing': Patient continuing established Avastin therapy
- 'first_treatment': This is clearly the patient's FIRST Avastin dose/cycle
- 'started': Recently started Avastin therapy (not first ever, but new)
- 'unknown': Cannot determine from available information

Return JSON format:
{{
    "steroid_status": "one of the above options",
    "steroid_details": "medication name and dose if available",
    "avastin_status": "one of the above options", 
    "avastin_details": "cycle number or dose if available",
    "confidence": 0.0-1.0,
    "evidence": ["direct quotes from the note supporting your extraction"]
}}"""
    
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response for medication information"""
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Extract medication status
            medication_status = {
                "steroid_status": data.get("steroid_status", "unknown"),
                "steroid_details": data.get("steroid_details", ""),
                "avastin_status": data.get("avastin_status", "unknown"),
                "avastin_details": data.get("avastin_details", "")
            }
            
            # Build reasoning from evidence
            evidence = data.get("evidence", [])
            reasoning = self._build_reasoning(medication_status, evidence)
            
            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            
            # Adjust confidence based on unknowns
            unknown_count = sum(1 for v in [medication_status["steroid_status"], 
                                           medication_status["avastin_status"]] 
                               if v == "unknown")
            if unknown_count > 0:
                confidence *= (1 - 0.3 * unknown_count)
            
            return medication_status, reasoning, confidence
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response}")
            # Fallback parsing
            return self._fallback_parse(response, context)
    
    def _build_reasoning(
        self,
        medication_status: Dict[str, str],
        evidence: list
    ) -> str:
        """Build reasoning from medication status and evidence"""
        
        parts = []
        
        # Steroid reasoning
        steroid = medication_status["steroid_status"]
        if steroid != "unknown":
            if steroid == "none":
                parts.append("No current steroid use")
            elif steroid == "stable":
                parts.append(f"Stable on steroids: {medication_status.get('steroid_details', 'dose unchanged')}")
            elif steroid == "increasing":
                parts.append(f"Steroid dose increased: {medication_status.get('steroid_details', 'escalation noted')}")
            elif steroid == "decreasing":
                parts.append(f"Steroid taper in progress: {medication_status.get('steroid_details', 'dose reduction')}")
            elif steroid == "started":
                parts.append(f"Newly started on steroids: {medication_status.get('steroid_details', 'initiation noted')}")
        
        # Avastin reasoning
        avastin = medication_status["avastin_status"]
        if avastin != "unknown":
            if avastin == "none":
                parts.append("Not on Avastin therapy")
            elif avastin == "ongoing":
                parts.append(f"Continuing Avastin: {medication_status.get('avastin_details', 'ongoing therapy')}")
            elif avastin == "first_treatment":
                parts.append(f"First Avastin treatment: {medication_status.get('avastin_details', 'initial dose')}")
            elif avastin == "started":
                parts.append(f"Recently started Avastin: {medication_status.get('avastin_details', 'new therapy')}")
        
        # Add evidence if available
        if evidence and len(evidence) > 0:
            parts.append(f"Based on: {evidence[0][:100]}...")
        
        return " | ".join(parts) if parts else "Medication status extracted from clinical note"
    
    def _fallback_parse(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Fallback parsing if JSON fails"""
        
        medication_status = {
            "steroid_status": "unknown",
            "steroid_details": "",
            "avastin_status": "unknown", 
            "avastin_details": ""
        }
        
        # Try to extract from text
        response_lower = response.lower()
        
        # Check steroid status
        if "no steroid" in response_lower or "not on steroid" in response_lower:
            medication_status["steroid_status"] = "none"
        elif "stable" in response_lower and any(pat in response_lower for pat in ["steroid", "dexamethasone"]):
            medication_status["steroid_status"] = "stable"
        elif "increas" in response_lower and any(pat in response_lower for pat in ["steroid", "dexamethasone"]):
            medication_status["steroid_status"] = "increasing"
        elif "decreas" in response_lower or "taper" in response_lower:
            medication_status["steroid_status"] = "decreasing"
        elif "started" in response_lower and any(pat in response_lower for pat in ["steroid", "dexamethasone"]):
            medication_status["steroid_status"] = "started"
        
        # Check Avastin status
        if "no avastin" in response_lower or "not on avastin" in response_lower:
            medication_status["avastin_status"] = "none"
        elif "first" in response_lower and "avastin" in response_lower:
            medication_status["avastin_status"] = "first_treatment"
        elif "ongoing" in response_lower or "continuing" in response_lower:
            medication_status["avastin_status"] = "ongoing"
        elif "started" in response_lower and "avastin" in response_lower:
            medication_status["avastin_status"] = "started"
        
        reasoning = "Extracted medication status using pattern matching (JSON parsing failed)"
        confidence = 0.4  # Lower confidence for fallback
        
        return medication_status, reasoning, confidence
    
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate medication extraction"""
        
        if not isinstance(extracted_value, dict):
            return False, "Invalid extraction format"
        
        # Validate steroid status
        valid_steroid_statuses = ["none", "stable", "increasing", "decreasing", "started", "unknown"]
        if extracted_value.get("steroid_status") not in valid_steroid_statuses:
            return False, f"Invalid steroid status: {extracted_value.get('steroid_status')}"
        
        # Validate Avastin status
        valid_avastin_statuses = ["none", "ongoing", "first_treatment", "started", "unknown"]
        if extracted_value.get("avastin_status") not in valid_avastin_statuses:
            return False, f"Invalid Avastin status: {extracted_value.get('avastin_status')}"
        
        # Check for logical consistency
        if (extracted_value.get("steroid_status") == "none" and 
            extracted_value.get("steroid_details", "").strip()):
            return False, "Inconsistent: No steroids but details provided"
        
        if (extracted_value.get("avastin_status") == "none" and 
            extracted_value.get("avastin_details", "").strip()):
            return False, "Inconsistent: No Avastin but details provided"
        
        return True, None
    
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for missing medication info"""
        return "Review medication list or contact pharmacy for current medication status"