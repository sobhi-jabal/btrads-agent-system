"""
Base agent class using vLLM for real LLM inference
Replaces mock implementation with production-ready agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import time
from datetime import datetime
import logging
import json
import re
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
import numpy as np

from models.agent import AgentResult, HighlightedSource, MissingInfo
from services.vllm_service import get_vllm_service, VLLMService

logger = logging.getLogger(__name__)

@dataclass
class ExtractionConfig:
    """Configuration for extraction tasks"""
    task_type: str
    complexity: str
    require_json: bool = True
    max_retries: int = 3
    confidence_threshold: float = 0.7

class VLLMBaseAgent(ABC):
    """Base class for BT-RADS agents using vLLM"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        extraction_config: ExtractionConfig,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.extraction_config = extraction_config
        
        # Initialize embedding model for source highlighting
        self.embedder = SentenceTransformer(embedding_model)
        
        # Cache for embeddings
        self._embedding_cache = {}
        
        # vLLM service will be initialized on first use
        self._vllm_service: Optional[VLLMService] = None
    
    async def _get_vllm_service(self) -> VLLMService:
        """Get or initialize vLLM service"""
        if self._vllm_service is None:
            self._vllm_service = await get_vllm_service()
        return self._vllm_service
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def build_extraction_prompt(
        self,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> str:
        """Build the extraction prompt"""
        pass
    
    @abstractmethod
    def parse_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Tuple[Any, str, float]:
        """Parse LLM response to extract value, reasoning, and confidence"""
        pass
    
    @abstractmethod
    def validate_extraction(
        self,
        extracted_value: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate the extracted value. Returns (is_valid, error_message)"""
        pass
    
    async def extract(
        self,
        clinical_note: str,
        context: Dict[str, Any],
        patient_id: str
    ) -> AgentResult:
        """Main extraction method with vLLM"""
        start_time = time.time()
        
        try:
            # Get vLLM service
            vllm = await self._get_vllm_service()
            
            # Build prompts
            system_prompt = self.get_system_prompt()
            user_prompt = self.build_extraction_prompt(clinical_note, context)
            
            # Log extraction start
            logger.info(f"{self.agent_id} processing patient {patient_id}")
            
            # Try extraction with retries
            response_text = None
            for attempt in range(self.extraction_config.max_retries):
                try:
                    # Call vLLM
                    result = await vllm.extract_btrads_info(
                        clinical_note=clinical_note,
                        extraction_type=self.agent_id,
                        context=context
                    )
                    
                    response_text = json.dumps(result["data"]) if isinstance(result["data"], dict) else str(result["data"])
                    
                    # Parse response
                    extracted_value, reasoning, confidence = self.parse_response(
                        response_text,
                        context
                    )
                    
                    # Validate extraction
                    is_valid, error_msg = self.validate_extraction(extracted_value, context)
                    
                    if is_valid and confidence >= self.extraction_config.confidence_threshold:
                        break
                    elif not is_valid:
                        logger.warning(f"Validation failed for {self.agent_id}: {error_msg}")
                        confidence *= 0.8
                    
                    if attempt < self.extraction_config.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed for {self.agent_id}: {e}")
                    if attempt == self.extraction_config.max_retries - 1:
                        raise
            
            # Find source highlights
            source_highlights = await self._find_source_highlights(
                clinical_note,
                extracted_value,
                reasoning
            )
            
            # Check for missing information
            missing_info = self._check_missing_info(
                extracted_value,
                confidence,
                context
            )
            
            # Calculate final processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Create result
            return AgentResult(
                agent_id=self.agent_id,
                patient_id=patient_id,
                node_id=self.agent_id,
                timestamp=datetime.utcnow(),
                extracted_value=extracted_value,
                confidence=confidence,
                reasoning=reasoning,
                source_highlights=source_highlights,
                missing_info=missing_info,
                processing_time_ms=processing_time_ms,
                llm_model=result.get("model", "unknown")
            )
            
        except Exception as e:
            logger.error(f"{self.agent_id} error: {str(e)}")
            return self._create_error_result(patient_id, str(e))
    
    async def _find_source_highlights(
        self,
        clinical_note: str,
        extracted_value: Any,
        reasoning: str
    ) -> List[HighlightedSource]:
        """Find and highlight relevant source sentences using embeddings"""
        
        # Split clinical note into sentences
        sentences = self._split_into_sentences(clinical_note)
        if not sentences:
            return []
        
        # Create query from extracted value and reasoning
        query = f"{extracted_value} {reasoning}"
        
        # Get embeddings
        query_embedding = self._get_embedding(query)
        sentence_embeddings = [self._get_embedding(sent) for sent in sentences]
        
        # Calculate similarities
        similarities = []
        for i, sent_emb in enumerate(sentence_embeddings):
            similarity = np.dot(query_embedding, sent_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(sent_emb)
            )
            similarities.append((similarity, i))
        
        # Sort by similarity and get top 3
        similarities.sort(reverse=True)
        top_sentences = similarities[:3]
        
        # Create highlights
        highlights = []
        for similarity, idx in top_sentences:
            if similarity > 0.5:  # Threshold for relevance
                sentence = sentences[idx]
                # Find sentence position in original text
                start = clinical_note.find(sentence)
                if start != -1:
                    end = start + len(sentence)
                    highlights.append(HighlightedSource(
                        text=sentence,
                        start_char=start,
                        end_char=end,
                        confidence=float(similarity)
                    ))
        
        return highlights
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting - can be improved with spaCy
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding with caching"""
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        embedding = self.embedder.encode(text)
        self._embedding_cache[text] = embedding
        return embedding
    
    def _check_missing_info(
        self,
        extracted_value: Any,
        confidence: float,
        context: Dict[str, Any]
    ) -> List[MissingInfo]:
        """Check for missing information"""
        missing = []
        
        # Check for low confidence
        if confidence < self.extraction_config.confidence_threshold:
            missing.append(MissingInfo(
                field=self.agent_id,
                reason=f"Low confidence extraction ({confidence:.2f})",
                clinical_impact="May affect downstream BT-RADS classification",
                suggested_fallback=self._get_fallback_suggestion()
            ))
        
        # Check for unknown/missing values
        if self._is_unknown_value(extracted_value):
            missing.append(MissingInfo(
                field=self.agent_id,
                reason="Could not extract required information from clinical note",
                clinical_impact="Missing data for BT-RADS decision node",
                suggested_fallback=self._get_fallback_suggestion()
            ))
        
        return missing
    
    def _is_unknown_value(self, value: Any) -> bool:
        """Check if value represents unknown/missing data"""
        if value is None:
            return True
        if isinstance(value, str) and value.lower() in ["unknown", "not found", "n/a", ""]:
            return True
        if isinstance(value, dict):
            return all(self._is_unknown_value(v) for v in value.values())
        return False
    
    @abstractmethod
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for missing info"""
        pass
    
    def _create_error_result(self, patient_id: str, error_msg: str) -> AgentResult:
        """Create an error result"""
        return AgentResult(
            agent_id=self.agent_id,
            patient_id=patient_id,
            node_id=self.agent_id,
            timestamp=datetime.utcnow(),
            extracted_value={"error": True, "message": error_msg},
            confidence=0.0,
            reasoning=f"Extraction failed: {error_msg}",
            source_highlights=[],
            missing_info=[MissingInfo(
                field=self.agent_id,
                reason=f"Agent error: {error_msg}",
                clinical_impact="Cannot proceed with this BT-RADS node",
                suggested_fallback="Manual review required"
            )],
            processing_time_ms=0,
            llm_model="error"
        )
    
    async def validate_result(
        self,
        result: AgentResult,
        feedback: Dict[str, Any]
    ) -> AgentResult:
        """Validate and update result based on clinician feedback"""
        result.validation_status = "validated"
        result.validated_value = feedback.get("value", result.extracted_value)
        result.validator_notes = feedback.get("notes", "")
        result.validated_at = datetime.utcnow()
        
        # Recalculate confidence if value changed
        if result.validated_value != result.extracted_value:
            result.confidence *= 0.9  # Slightly reduce confidence
            result.reasoning += f" [Validated: {feedback.get('notes', 'Clinician correction')}]"
        
        return result