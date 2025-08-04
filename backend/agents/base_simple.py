"""Simplified base agent class for BT-RADS system"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime
import logging
import json
import ollama
from ollama import Options

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
    
    def _chunk_clinical_note(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """Split clinical note into overlapping chunks like the old implementation"""
        if len(text) <= chunk_size * 2:
            return [text]  # Return full text if it's short enough
        
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def _extract_relevant_context(self, clinical_note: str, query_keywords: List[str], max_context: int = 8000) -> str:
        """Return truncated clinical note for llama3.2's context window"""
        # Truncate to a reasonable size for llama3.2
        # Focus on the most recent/relevant parts
        return clinical_note[:max_context] if len(clinical_note) > max_context else clinical_note
    
    async def _call_llm(self, prompt: str, output_format: str = "json") -> Dict[str, Any]:
        """Call Ollama LLM with the prompt"""
        logger.info(f"[DEBUG] _call_llm called with prompt length: {len(prompt)}")
        try:
            # Configure Ollama options for llama3.2
            options = Options(
                temperature=0.1,
                top_k=40,
                top_p=0.95,
                num_ctx=8192,  # Reasonable context for llama3.2
                num_predict=512,  # Enough for JSON output
                repeat_penalty=1.1,
                seed=42
            )
            
            # Prepare messages for chat format
            messages = [
                {"role": "system", "content": "You are an expert medical data extractor for BT-RADS brain tumor classification."},
                {"role": "user", "content": prompt}
            ]
            
            # Try up to 3 times with retries
            for attempt in range(3):
                try:
                    logger.info(f"[DEBUG] Calling Ollama with llama3.2:latest, attempt {attempt+1}/3")
                    
                    # Use Ollama AsyncClient directly
                    from ollama import AsyncClient
                    client = AsyncClient()
                    
                    # Call with timeout - reasonable for llama3.2
                    timeout_seconds = 60  # 1 minute timeout for llama3.2
                    
                    try:
                        response = await asyncio.wait_for(
                            client.chat(
                                model="llama3.2:latest",
                                format="json" if output_format == "json" else None,
                                keep_alive="10m",
                                options=options,
                                messages=messages
                            ),
                            timeout=timeout_seconds
                        )
                        logger.info(f"[DEBUG] Ollama returned response")
                    except asyncio.TimeoutError:
                        logger.error(f"Ollama timeout after {timeout_seconds} seconds on attempt {attempt+1}/3")
                        raise TimeoutError(f"Ollama did not respond within {timeout_seconds} seconds")
                    
                    content = response.get("message", {}).get("content", "")
                    if not content.strip():
                        raise ValueError("Empty response from Ollama")
                    
                    # Parse JSON response
                    if output_format == "json":
                        try:
                            # Try to parse as JSON
                            parsed = json.loads(content)
                            return parsed
                        except json.JSONDecodeError:
                            # Try to extract JSON from text
                            start = content.find("{")
                            end = content.rfind("}") + 1
                            if start >= 0 and end > start:
                                json_str = content[start:end]
                                parsed = json.loads(json_str)
                                return parsed
                            raise ValueError(f"Could not parse JSON from response: {content[:200]}")
                    else:
                        return {"text": content}
                        
                except Exception as e:
                    logger.warning(f"Ollama attempt {attempt+1}/3 failed: {e}")
                    if attempt < 2:
                        await asyncio.sleep(2)
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"Ollama LLM call failed: {e}")
            # Return error response (no fallback to mock data)
            return {
                "error": True,
                "message": str(e),
                "confidence": 0.0,
                "reasoning": f"LLM extraction failed: {e}"
            }
    
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
            llm_model="phi4:14b"
        )
    
    async def validate(self, result: AgentResult, feedback: Dict[str, Any]) -> AgentResult:
        """Default validation method"""
        result.validation_status = "validated"
        result.validated_value = feedback.get("value", result.extracted_value)
        result.validator_notes = feedback.get("notes", "")
        return result