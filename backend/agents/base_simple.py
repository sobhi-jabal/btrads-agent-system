"""Simplified base agent class for BT-RADS system"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime
import logging
import json

from models.agent import AgentResult, HighlightedSource

logger = logging.getLogger(__name__)

class SimpleBaseAgent(ABC):
    """Simplified base class for BT-RADS agents"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        
    @abstractmethod
    async def extract(
        self,
        clinical_note: str,
        context: Dict[str, Any],
        patient_id: str
    ) -> AgentResult:
        """Main extraction method - must be implemented by each agent"""
        pass
    
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Mock LLM call for now - returns structured data"""
        # In production, this would call Ollama
        # For now, return mock data based on the agent type
        mock_responses = {
            "prior-assessment": {
                "has_prior": True,
                "confidence": 0.85,
                "reasoning": "Found mention of prior imaging",
                "evidence_sentences": ["Prior MRI from 6 months ago shows..."]
            },
            "imaging-comparison": {
                "volume_change": 25.5,
                "change_type": "increase",
                "confidence": 0.9,
                "reasoning": "Clear volume measurements provided",
                "evidence_sentences": ["FLAIR volume increased by 25.5%"]
            },
            "medication-status": {
                "on_medication": True,
                "medication_type": "corticosteroids",
                "confidence": 0.8,
                "reasoning": "Patient on dexamethasone",
                "evidence_sentences": ["Currently on dexamethasone 4mg daily"]
            },
            "radiation-timeline": {
                "radiation_date_str": "2024-01-15",
                "radiation_type": "stereotactic radiosurgery",
                "confidence": 0.9,
                "reasoning": "Found radiation date",
                "evidence_sentences": ["Completed SRS on January 15, 2024"]
            },
            "component-analysis": {
                "enhancement_pattern": "peripheral",
                "necrosis_present": True,
                "confidence": 0.85,
                "reasoning": "Peripheral enhancement with central necrosis",
                "evidence_sentences": ["Shows peripheral enhancement with central necrosis"]
            },
            "extent-analysis": {
                "extent": "multifocal",
                "locations": ["frontal", "parietal"],
                "confidence": 0.9,
                "reasoning": "Multiple lesions noted",
                "evidence_sentences": ["Multifocal lesions in frontal and parietal lobes"]
            },
            "progression-pattern": {
                "pattern": "local",
                "confidence": 0.85,
                "reasoning": "Progression at treatment site",
                "evidence_sentences": ["Local progression at the treatment site"]
            }
        }
        
        await asyncio.sleep(0.5)  # Simulate processing time
        return mock_responses.get(self.agent_id, {
            "confidence": 0.5,
            "reasoning": "Default mock response",
            "evidence_sentences": []
        })
    
    async def _highlight_sources(
        self,
        clinical_note: str,
        evidence_sentences: List[str]
    ) -> List[HighlightedSource]:
        """Find source highlights in the clinical note"""
        highlights = []
        
        for sentence in evidence_sentences:
            # Simple substring search for now
            if sentence in clinical_note:
                start = clinical_note.find(sentence)
                end = start + len(sentence)
                highlights.append(HighlightedSource(
                    text=sentence,
                    start_char=start,
                    end_char=end,
                    confidence=0.9
                ))
        
        return highlights
    
    def _create_error_result(self, patient_id: str, error_msg: str) -> AgentResult:
        """Create an error result"""
        return AgentResult(
            agent_id=self.agent_id,
            patient_id=patient_id,
            node_id=self.agent_id,
            timestamp=datetime.utcnow(),
            extracted_value={"error": True, "message": error_msg},
            confidence=0.0,
            reasoning=f"Error: {error_msg}",
            source_highlights=[],
            processing_time_ms=0,
            llm_model="mock-llm"
        )
    
    async def validate(self, result: AgentResult, feedback: Dict[str, Any]) -> AgentResult:
        """Default validation method"""
        result.validation_status = "validated"
        result.validated_value = feedback.get("value", result.extracted_value)
        result.validator_notes = feedback.get("notes", "")
        return result