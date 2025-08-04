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
            # Use full clinical note (no RAG chunking)
            medication_keywords = [
                'steroid', 'dexamethasone', 'decadron', 'prednisone', 'prednisolone',
                'avastin', 'bevacizumab', 'anti-angiogenic', 'medication', 'drug',
                'dose', 'mg', 'taper', 'increase', 'decrease', 'started', 'discontinued'
            ]
            relevant_context = self._extract_relevant_context(clinical_note, medication_keywords)
            
            # Create prompt for medication extraction with chunked context
            prompt = f"""Extract medication information from this clinical note.

Clinical Note:
{relevant_context}

Instructions:
1. Look for STEROIDS (dexamethasone, decadron, prednisone, prednisolone)
2. Look for AVASTIN (Avastin, bevacizumab, anti-angiogenic)
3. Determine the CURRENT status for each medication

Return a JSON object with EXACTLY this structure:
{{
    "steroid_status": "stable",
    "avastin_status": "ongoing",
    "reasoning": "Found evidence that patient is on dexamethasone 4mg daily and continuing Avastin therapy",
    "confidence": 0.8,
    "evidence_sentences": ["Patient continues on dexamethasone 4mg daily", "Avastin 10mg/kg every 2 weeks"]
}}

Valid values for steroid_status: none, stable, increasing, decreasing, started, unknown
Valid values for avastin_status: none, ongoing, first_treatment, started, unknown

IMPORTANT: You MUST return valid JSON with all 5 fields (steroid_status, avastin_status, reasoning, confidence, evidence_sentences)."""
            
            # Get LLM response with JSON format
            response = await self._call_llm(prompt, output_format="json")
            
            # Check if LLM call failed
            if response.get("error", False):
                # Return unknown values when LLM fails
                medication_status = {
                    "steroid_status": "unknown",
                    "avastin_status": "unknown"
                }
                logger.warning(f"LLM extraction failed, using unknown values: {response.get('message', 'Unknown error')}")
            else:
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
                llm_model="phi4:14b"
            )
            
        except Exception as e:
            logger.error(f"Error in MedicationStatusAgent: {e}")
            return self._create_error_result(patient_id, str(e))