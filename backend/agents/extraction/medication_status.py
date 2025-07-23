"""Agent for extracting medication status"""
from typing import Dict, Any
import logging
import time
from datetime import datetime

from agents.base_simple import SimpleBaseAgent
from models.agent import AgentResult

logger = logging.getLogger(__name__)

class MedicationStatusAgent(SimpleBaseAgent):
    """Agent for extracting current medication status"""
    
    def __init__(self):
        super().__init__(
            agent_id="medication-status",
            name="Medication Status Agent",
            description="Extracts current steroid and Avastin medication status"
        )
    
    async def extract(self, clinical_note: str, context: Dict[str, Any], patient_id: str) -> AgentResult:
        """Extract medication status from clinical note"""
        start_time = time.time()
        try:
            # Create prompt for medication extraction
            prompt = f"""
            You are an expert medical data extractor specializing in brain tumor patient medication management.
            Your task is to extract CURRENT medication status with high precision.
            
            Clinical Note:
            {clinical_note}
            
            Extract CURRENT medication status from the clinical note.
            
            STEROID STATUS - Look for dexamethasone, decadron, prednisolone, prednisone:
            - 'none': Patient is not currently on steroids
            - 'stable': Patient continues on same steroid dose  
            - 'increasing': Steroid dose being increased/escalated
            - 'decreasing': Steroid dose being tapered/decreased
            - 'started': Patient newly started on steroids
            - 'unknown': Cannot determine from available information
            
            AVASTIN STATUS - Look for Avastin, bevacizumab, BV, anti-angiogenic therapy:
            - 'none': Patient is not on Avastin therapy
            - 'ongoing': Patient continuing established Avastin therapy
            - 'first_treatment': This is clearly the patient's first Avastin dose/cycle
            - 'started': Recently started Avastin therapy  
            - 'unknown': Cannot determine from available information
            
            Focus on CURRENT status only. Be conservative - use 'unknown' if uncertain.
            
            Return JSON format:
            {{
                "steroid_status": "none/stable/increasing/decreasing/started/unknown",
                "avastin_status": "none/ongoing/first_treatment/started/unknown",
                "reasoning": "explanation",
                "confidence": 0.0-1.0,
                "evidence_sentences": ["relevant quotes"]
            }}
            """
            
            # Get LLM response
            response = await self._call_llm(prompt)
            
            # Extract the medication status
            medication_status = {
                "steroid_status": response.get("steroid_status", "unknown"),
                "avastin_status": response.get("avastin_status", "unknown")
            }
            
            # Calculate confidence based on how many unknowns
            unknown_count = sum(1 for v in medication_status.values() if v == "unknown")
            confidence = response.get("confidence", 1.0 - (unknown_count * 0.4))
            
            # Find source highlights
            source_highlights = await self._highlight_sources(
                clinical_note,
                response.get("evidence_sentences", [])
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                agent_id=self.agent_id,
                patient_id=patient_id,
                node_id="medication_status",
                timestamp=datetime.utcnow(),
                extracted_value=medication_status,
                confidence=confidence,
                reasoning=response.get("reasoning", f"Steroid status: {medication_status['steroid_status']}, Avastin status: {medication_status['avastin_status']}"),
                source_highlights=source_highlights,
                processing_time_ms=processing_time,
                llm_model="mock-llm"
            )
            
        except Exception as e:
            logger.error(f"Error in MedicationStatusAgent: {e}")
            return self._create_error_result(patient_id, str(e))