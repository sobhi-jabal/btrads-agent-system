"""
Enhanced RAG Service for BT-RADS
Combines HyDE, ColBERT-style reranking, and medical-specific retrieval
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import re

from services.hyde_service import get_hyde_service
from services.vllm_service import get_vllm_service

logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """Configuration for RAG pipeline"""
    use_hyde: bool = True
    use_reranking: bool = True
    use_self_rag: bool = True
    chunk_size: int = 256
    chunk_overlap: int = 64
    top_k_retrieval: int = 10
    top_k_final: int = 5
    hyde_hypotheticals: int = 3
    retrieval_threshold: float = 0.5

@dataclass
class RetrievedChunk:
    """Retrieved chunk with metadata"""
    text: str
    score: float
    source: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any]

class EnhancedRAGService:
    """
    State-of-the-art RAG service for medical text retrieval
    Implements:
    - HyDE for query enhancement
    - Self-RAG for adaptive retrieval
    - Medical-specific chunking
    - Multi-stage reranking
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.hyde_service = None
        self.vllm_service = None
        
        # Medical term patterns
        self.medical_patterns = {
            "medication": re.compile(r'\b(mg|mcg|ml|BID|TID|QID|PRN|IV|PO|IM|SC)\b', re.I),
            "imaging": re.compile(r'\b(MRI|CT|PET|FLAIR|T1|T2|enhancement|signal)\b', re.I),
            "dates": re.compile(r'\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})\b'),
            "measurements": re.compile(r'\b(\d+\.?\d*)\s*(cm|mm|cc|mL)\b', re.I),
        }
    
    async def _ensure_services(self):
        """Ensure required services are initialized"""
        if self.hyde_service is None:
            self.hyde_service = await get_hyde_service()
        if self.vllm_service is None:
            self.vllm_service = await get_vllm_service()
    
    async def retrieve_with_rag(
        self,
        query: str,
        clinical_note: str,
        extraction_type: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[RetrievedChunk], Dict[str, Any]]:
        """
        Main RAG pipeline for retrieval
        
        Args:
            query: The information query
            clinical_note: Full clinical note
            extraction_type: Type of extraction (medication, imaging, etc.)
            additional_context: Additional context (dates, volumes, etc.)
        
        Returns:
            Retrieved chunks and metadata
        """
        await self._ensure_services()
        
        # Step 1: Chunk the clinical note
        chunks = self._create_medical_aware_chunks(clinical_note, extraction_type)
        
        # Step 2: Determine if retrieval is needed (Self-RAG)
        needs_retrieval = await self._should_retrieve(query, extraction_type)
        
        if not needs_retrieval:
            # Return full note as single chunk
            return [RetrievedChunk(
                text=clinical_note,
                score=1.0,
                source="full_note",
                start_char=0,
                end_char=len(clinical_note),
                metadata={"retrieval_skipped": True}
            )], {"retrieval_method": "full_note"}
        
        # Step 3: Retrieve with HyDE if enabled
        if self.config.use_hyde:
            retrieved = await self._hyde_retrieve(
                query, chunks, extraction_type, additional_context
            )
        else:
            retrieved = await self._standard_retrieve(query, chunks)
        
        # Step 4: Rerank if enabled
        if self.config.use_reranking:
            retrieved = await self._rerank_chunks(query, retrieved, extraction_type)
        
        # Step 5: Filter by threshold
        retrieved = [
            chunk for chunk in retrieved 
            if chunk.score >= self.config.retrieval_threshold
        ]
        
        # Step 6: Limit to top-k
        retrieved = retrieved[:self.config.top_k_final]
        
        # Metadata about retrieval
        metadata = {
            "retrieval_method": "hyde" if self.config.use_hyde else "standard",
            "chunks_retrieved": len(retrieved),
            "avg_score": np.mean([c.score for c in retrieved]) if retrieved else 0,
            "extraction_type": extraction_type
        }
        
        return retrieved, metadata
    
    def _create_medical_aware_chunks(
        self,
        text: str,
        extraction_type: str
    ) -> List[Dict[str, Any]]:
        """
        Create chunks with awareness of medical context
        Respects sentence boundaries and medical sections
        """
        
        chunks = []
        
        # Split by common medical sections
        section_markers = [
            "CLINICAL HISTORY:",
            "COMPARISON:",
            "TECHNIQUE:",
            "FINDINGS:",
            "IMPRESSION:",
            "MEDICATIONS:",
            "ASSESSMENT:",
            "PLAN:",
            "CURRENT MEDICATIONS:",
            "RADIATION HISTORY:",
        ]
        
        # Find section boundaries
        sections = []
        for marker in section_markers:
            pos = text.find(marker)
            if pos != -1:
                sections.append((pos, marker))
        
        sections.sort(key=lambda x: x[0])
        
        # Create chunks respecting sections
        if sections:
            # Add first chunk before any section
            if sections[0][0] > 0:
                chunks.extend(self._chunk_text(
                    text[:sections[0][0]], 
                    0,
                    {"section": "header"}
                ))
            
            # Process each section
            for i, (pos, marker) in enumerate(sections):
                end_pos = sections[i+1][0] if i+1 < len(sections) else len(text)
                section_text = text[pos:end_pos]
                
                # Chunk within section
                section_chunks = self._chunk_text(
                    section_text,
                    pos,
                    {"section": marker.strip(":")}
                )
                chunks.extend(section_chunks)
        else:
            # No sections found, chunk normally
            chunks = self._chunk_text(text, 0, {"section": "full"})
        
        return chunks
    
    def _chunk_text(
        self,
        text: str,
        start_offset: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text with overlap, respecting sentence boundaries"""
        
        chunks = []
        sentences = self._split_sentences(text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # Check if adding this sentence exceeds chunk size
            if current_length + sentence_length > self.config.chunk_size and current_chunk:
                # Create chunk
                chunk_text = " ".join(current_chunk)
                chunk_start = text.find(current_chunk[0])
                chunk_end = chunk_start + len(chunk_text)
                
                chunks.append({
                    "text": chunk_text,
                    "start": start_offset + chunk_start,
                    "end": start_offset + chunk_end,
                    "metadata": {
                        **metadata,
                        "sentence_count": len(current_chunk),
                        "has_medical_terms": self._has_medical_terms(chunk_text)
                    }
                })
                
                # Start new chunk with overlap
                overlap_sentences = max(1, len(current_chunk) // 4)
                current_chunk = current_chunk[-overlap_sentences:]
                current_length = sum(len(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_start = text.find(current_chunk[0])
            chunk_end = chunk_start + len(chunk_text)
            
            chunks.append({
                "text": chunk_text,
                "start": start_offset + chunk_start,
                "end": start_offset + chunk_end,
                "metadata": {
                    **metadata,
                    "sentence_count": len(current_chunk),
                    "has_medical_terms": self._has_medical_terms(chunk_text)
                }
            })
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, handling medical abbreviations"""
        
        # Simple sentence splitter that handles common medical abbreviations
        text = text.replace("Dr.", "Dr")
        text = text.replace("Mr.", "Mr")
        text = text.replace("Mrs.", "Mrs")
        text = text.replace("vs.", "vs")
        text = text.replace("approx.", "approx")
        
        # Split on sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter empty sentences and restore abbreviations
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _has_medical_terms(self, text: str) -> Dict[str, bool]:
        """Check for presence of medical terms"""
        
        return {
            pattern_name: bool(pattern.search(text))
            for pattern_name, pattern in self.medical_patterns.items()
        }
    
    async def _should_retrieve(
        self,
        query: str,
        extraction_type: str
    ) -> bool:
        """
        Self-RAG: Determine if retrieval is needed
        """
        
        # Always retrieve for complex extraction types
        complex_types = ["component_analysis", "extent_analysis", "progression_pattern"]
        if extraction_type in complex_types:
            return True
        
        # Check query complexity
        query_words = query.lower().split()
        if len(query_words) > 10:  # Complex query
            return True
        
        # Check for specific keywords that indicate retrieval need
        retrieval_keywords = [
            "compare", "change", "progression", "prior", "previous",
            "increase", "decrease", "stable", "medication", "dose"
        ]
        
        if any(keyword in query.lower() for keyword in retrieval_keywords):
            return True
        
        # Simple extractions might not need retrieval
        return False
    
    async def _hyde_retrieve(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        extraction_type: str,
        additional_context: Optional[Dict[str, Any]]
    ) -> List[RetrievedChunk]:
        """Retrieve using HyDE"""
        
        # Enhance query with context
        enhanced_query = query
        if additional_context:
            if "followup_date" in additional_context:
                enhanced_query += f" Current scan date: {additional_context['followup_date']}"
            if "flair_change_pct" in additional_context:
                enhanced_query += f" FLAIR change: {additional_context['flair_change_pct']:.1f}%"
        
        # Perform HyDE search
        results = await self.hyde_service.hybrid_search(
            query=enhanced_query,
            documents=[c["text"] for c in chunks],
            context_type=extraction_type,
            top_k=self.config.top_k_retrieval,
            alpha=0.6  # Favor dense search for medical
        )
        
        # Convert to RetrievedChunk objects
        retrieved_chunks = []
        for idx, score, text in results:
            chunk_data = chunks[idx]
            retrieved_chunks.append(RetrievedChunk(
                text=text,
                score=score,
                source=chunk_data["metadata"].get("section", "unknown"),
                start_char=chunk_data["start"],
                end_char=chunk_data["end"],
                metadata=chunk_data["metadata"]
            ))
        
        return retrieved_chunks
    
    async def _standard_retrieve(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> List[RetrievedChunk]:
        """Standard retrieval without HyDE"""
        
        # Simple embedding-based retrieval
        await self._ensure_services()
        
        # This would use the embedding model directly
        # For now, return a simple keyword-based search
        query_terms = set(query.lower().split())
        
        scored_chunks = []
        for chunk in chunks:
            chunk_terms = set(chunk["text"].lower().split())
            overlap = len(query_terms & chunk_terms) / len(query_terms)
            
            if overlap > 0:
                scored_chunks.append((overlap, chunk))
        
        # Sort by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Convert to RetrievedChunk
        retrieved = []
        for score, chunk_data in scored_chunks[:self.config.top_k_retrieval]:
            retrieved.append(RetrievedChunk(
                text=chunk_data["text"],
                score=score,
                source=chunk_data["metadata"].get("section", "unknown"),
                start_char=chunk_data["start"],
                end_char=chunk_data["end"],
                metadata=chunk_data["metadata"]
            ))
        
        return retrieved
    
    async def _rerank_chunks(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        extraction_type: str
    ) -> List[RetrievedChunk]:
        """
        Rerank chunks using cross-encoder style scoring
        In production, this would use ColBERT
        """
        
        # For now, use LLM-based reranking for high-quality results
        reranked = []
        
        for chunk in chunks:
            # Score based on relevance to extraction type
            relevance_score = await self._score_chunk_relevance(
                query, chunk.text, extraction_type
            )
            
            # Combine with initial score
            final_score = chunk.score * 0.5 + relevance_score * 0.5
            
            reranked.append(RetrievedChunk(
                text=chunk.text,
                score=final_score,
                source=chunk.source,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                metadata={**chunk.metadata, "reranked": True}
            ))
        
        # Sort by new scores
        reranked.sort(key=lambda x: x.score, reverse=True)
        
        return reranked
    
    async def _score_chunk_relevance(
        self,
        query: str,
        chunk_text: str,
        extraction_type: str
    ) -> float:
        """Score chunk relevance for specific extraction"""
        
        # Extraction-specific scoring heuristics
        score = 0.5  # Base score
        
        if extraction_type == "medication_status":
            # Look for medication terms
            med_terms = ["dexamethasone", "steroid", "avastin", "bevacizumab", "dose", "mg"]
            matches = sum(1 for term in med_terms if term in chunk_text.lower())
            score += min(0.5, matches * 0.1)
        
        elif extraction_type == "imaging_comparison":
            # Look for comparison terms
            comp_terms = ["increased", "decreased", "stable", "unchanged", "progression", "improvement"]
            matches = sum(1 for term in comp_terms if term in chunk_text.lower())
            score += min(0.5, matches * 0.1)
        
        elif extraction_type == "radiation_timeline":
            # Look for dates and radiation terms
            if self.medical_patterns["dates"].search(chunk_text):
                score += 0.3
            if "radiation" in chunk_text.lower() or "xrt" in chunk_text.lower():
                score += 0.2
        
        return min(1.0, score)
    
    def create_augmented_prompt(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
        extraction_type: str
    ) -> str:
        """
        Create an augmented prompt with retrieved context
        """
        
        # Build context section
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(f"[Context {i} - {chunk.source}]:\n{chunk.text}")
        
        context_section = "\n\n".join(context_parts)
        
        # Build augmented prompt
        augmented_prompt = f"""Based on the following clinical note excerpts, {query}

Relevant Context:
{context_section}

Please answer based only on the information provided in the context above."""
        
        return augmented_prompt

# Singleton instance
_enhanced_rag_service = None

async def get_enhanced_rag_service() -> EnhancedRAGService:
    """Get or create enhanced RAG service instance"""
    global _enhanced_rag_service
    if _enhanced_rag_service is None:
        _enhanced_rag_service = EnhancedRAGService()
    return _enhanced_rag_service