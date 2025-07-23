"""Base agent class for BT-RADS system"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import time
from datetime import datetime
import logging

from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from sentence_transformers import SentenceTransformer

from models.agent import AgentResult, HighlightedSource, MissingInfo
from utils.text_processing import find_relevant_sentences, calculate_sentence_relevance

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all BT-RADS agents"""
    
    def __init__(
        self,
        agent_id: str,
        node_id: str,
        llm_model: str = "llama3:8b",
        temperature: float = 0.0,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.agent_id = agent_id
        self.node_id = node_id
        self.llm_model = llm_model
        self.temperature = temperature
        
        # Initialize LLM
        self.llm = Ollama(
            model=llm_model,
            temperature=temperature,
            num_ctx=8192,
            num_predict=512
        )
        
        # Initialize embedding model for source highlighting
        self.embedder = SentenceTransformer(embedding_model)
        
        # Agent-specific configuration
        self.system_prompt = self._get_system_prompt()
        self.extraction_prompt = self._get_extraction_prompt()
        
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def _get_extraction_prompt(self) -> PromptTemplate:
        """Get the extraction prompt template"""
        pass
    
    @abstractmethod
    def _parse_llm_response(self, response: str) -> Tuple[Any, str, float]:
        """Parse the LLM response to extract value, reasoning, and confidence"""
        pass
    
    @abstractmethod
    def _validate_extraction(self, value: Any, context: Dict[str, Any]) -> bool:
        """Validate the extracted value against context"""
        pass
    
    async def extract(
        self,
        clinical_note: str,
        context: Dict[str, Any],
        patient_id: str
    ) -> AgentResult:
        """Main extraction method"""
        start_time = time.time()
        
        try:
            # Prepare the prompt
            prompt = self._prepare_prompt(clinical_note, context)
            
            # Get LLM response
            logger.info(f"{self.agent_id} processing patient {patient_id}")
            response = await self._get_llm_response(prompt)
            
            # Parse response
            extracted_value, reasoning, confidence = self._parse_llm_response(response)
            
            # Validate extraction
            is_valid = self._validate_extraction(extracted_value, context)
            if not is_valid:
                confidence *= 0.8  # Reduce confidence for questionable extractions
            
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
            
            # Create result
            result = AgentResult(
                agent_id=self.agent_id,
                node_id=self.node_id,
                patient_id=patient_id,
                timestamp=datetime.utcnow(),
                extracted_value=extracted_value,
                confidence=confidence,
                reasoning=reasoning,
                source_highlights=source_highlights,
                missing_info=missing_info,
                processing_time_ms=int((time.time() - start_time) * 1000),
                llm_model=self.llm_model
            )
            
            logger.info(
                f"{self.agent_id} completed: value={extracted_value}, "
                f"confidence={confidence:.2f}, time={result.processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"{self.agent_id} error: {str(e)}")
            # Return error result
            return AgentResult(
                agent_id=self.agent_id,
                node_id=self.node_id,
                patient_id=patient_id,
                timestamp=datetime.utcnow(),
                extracted_value="error",
                confidence=0.0,
                reasoning=f"Extraction failed: {str(e)}",
                source_highlights=[],
                missing_info=[MissingInfo(
                    field="extraction",
                    reason=f"Agent error: {str(e)}",
                    clinical_impact="Cannot proceed with this node",
                    suggested_fallback="Manual review required"
                )],
                processing_time_ms=int((time.time() - start_time) * 1000),
                llm_model=self.llm_model
            )
    
    def _prepare_prompt(self, clinical_note: str, context: Dict[str, Any]) -> str:
        """Prepare the prompt with clinical note and context"""
        prompt_vars = {
            "clinical_note": clinical_note,
            "system_prompt": self.system_prompt,
            **context
        }
        return self.extraction_prompt.format(**prompt_vars)
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.llm.invoke(prompt)
        )
        return response
    
    async def _find_source_highlights(
        self,
        clinical_note: str,
        extracted_value: Any,
        reasoning: str
    ) -> List[HighlightedSource]:
        """Find and highlight relevant source sentences"""
        # Combine extracted value and reasoning for search
        search_query = f"{extracted_value} {reasoning}"
        
        # Find relevant sentences
        relevant_sentences = find_relevant_sentences(
            clinical_note,
            search_query,
            self.embedder,
            top_k=3
        )
        
        # Convert to HighlightedSource objects
        highlights = []
        for sent_text, start, end, relevance in relevant_sentences:
            highlights.append(HighlightedSource(
                text=sent_text,
                start_char=start,
                end_char=end,
                confidence=relevance
            ))
        
        return highlights
    
    def _check_missing_info(
        self,
        extracted_value: Any,
        confidence: float,
        context: Dict[str, Any]
    ) -> List[MissingInfo]:
        """Check for missing information"""
        missing = []
        
        # Common check for "unknown" values
        if extracted_value == "unknown" or confidence < 0.5:
            missing.append(MissingInfo(
                field=self.node_id,
                reason="Could not extract reliable information",
                clinical_impact="May affect downstream decisions",
                suggested_fallback=self._get_fallback_suggestion()
            ))
        
        return missing
    
    @abstractmethod
    def _get_fallback_suggestion(self) -> str:
        """Get fallback suggestion for missing info"""
        pass