"""
HyDE (Hypothetical Document Embeddings) Service
Generates hypothetical documents to improve retrieval for medical queries
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import numpy as np

from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import faiss

from services.vllm_service import get_vllm_service

logger = logging.getLogger(__name__)

class HyDEService:
    """
    Implements Hypothetical Document Embeddings for medical text retrieval
    Combines with BM25 for hybrid search and uses reranking for precision
    """
    
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",
        use_medical_model: bool = True
    ):
        # Initialize embedding model
        if use_medical_model:
            # Use medical-specific embeddings if available
            try:
                self.embedder = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
                logger.info("Using medical-specific embedding model")
            except:
                logger.warning("Medical embedding model not available, using general model")
                self.embedder = SentenceTransformer(embedding_model)
        else:
            self.embedder = SentenceTransformer(embedding_model)
        
        # Cache for hypothetical documents
        self.hyde_cache = {}
        
        # Initialize reranker (would use ColBERT in production)
        self.reranker = None  # Will be initialized when needed
    
    async def generate_hypothetical_answer(
        self,
        query: str,
        context_type: str = "medical",
        num_hypotheticals: int = 3
    ) -> List[str]:
        """
        Generate hypothetical answers for a query using LLM
        
        Args:
            query: The search query
            context_type: Type of context (medical, radiology, medication)
            num_hypotheticals: Number of hypothetical documents to generate
        
        Returns:
            List of hypothetical answers
        """
        
        # Check cache
        cache_key = f"{query}_{context_type}_{num_hypotheticals}"
        if cache_key in self.hyde_cache:
            return self.hyde_cache[cache_key]
        
        # Get vLLM service
        vllm = await get_vllm_service()
        
        # Build prompt based on context type
        system_prompt = self._get_hyde_system_prompt(context_type)
        user_prompt = self._build_hyde_prompt(query, context_type, num_hypotheticals)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Generate hypothetical documents
        response = await vllm.chat_completion(
            messages=messages,
            model="mixtral-8x7b",  # Fast model for hypothesis generation
            temperature=0.7,  # Higher temperature for diversity
            max_tokens=512 * num_hypotheticals
        )
        
        # Parse response
        content = response["choices"][0]["message"]["content"]
        hypotheticals = self._parse_hypothetical_documents(content, num_hypotheticals)
        
        # Cache results
        self.hyde_cache[cache_key] = hypotheticals
        
        return hypotheticals
    
    def _get_hyde_system_prompt(self, context_type: str) -> str:
        """Get system prompt for HyDE generation"""
        
        prompts = {
            "medical": """You are a medical expert creating hypothetical clinical note excerpts.
Your task is to generate realistic medical documentation that would contain the answer to a query.
Focus on clinical accuracy, medical terminology, and typical documentation patterns.""",
            
            "radiology": """You are a neuroradiologist creating hypothetical radiology report excerpts.
Generate realistic imaging findings and interpretations that would answer the query.
Use standard radiology terminology and reporting conventions.""",
            
            "medication": """You are a clinical pharmacist creating hypothetical medication documentation.
Generate realistic medication notes including dosing, changes, and clinical reasoning.
Include relevant drug names, doses, and administration details.""",
            
            "btrads": """You are a neuro-oncologist documenting BT-RADS assessments.
Generate hypothetical clinical documentation relevant to brain tumor follow-up.
Include imaging comparisons, treatment effects, and progression assessments."""
        }
        
        return prompts.get(context_type, prompts["medical"])
    
    def _build_hyde_prompt(self, query: str, context_type: str, num_hypotheticals: int) -> str:
        """Build prompt for generating hypothetical documents"""
        
        return f"""Given this question: "{query}"

Generate {num_hypotheticals} different hypothetical clinical note excerpts that would contain the answer to this question.
Each excerpt should be 2-3 sentences of realistic medical documentation.

Make each excerpt different but relevant. Use appropriate medical terminology.

Format your response as:
EXCERPT 1:
[Your first hypothetical excerpt]

EXCERPT 2:
[Your second hypothetical excerpt]

EXCERPT 3:
[Your third hypothetical excerpt]"""
    
    def _parse_hypothetical_documents(self, response: str, expected_count: int) -> List[str]:
        """Parse hypothetical documents from LLM response"""
        
        excerpts = []
        
        # Split by EXCERPT markers
        parts = response.split("EXCERPT")
        
        for part in parts[1:]:  # Skip first part before "EXCERPT 1"
            # Extract content after the number and colon
            if ":" in part:
                content = part.split(":", 1)[1].strip()
                if content:
                    excerpts.append(content)
        
        # Fallback: if parsing fails, split by double newlines
        if len(excerpts) < expected_count:
            excerpts = [p.strip() for p in response.split("\n\n") if p.strip()]
        
        # Ensure we have the expected number
        excerpts = excerpts[:expected_count]
        
        # Pad with original query if needed
        while len(excerpts) < expected_count:
            excerpts.append(f"Clinical note regarding: {response[:200]}")
        
        return excerpts
    
    async def hyde_search(
        self,
        query: str,
        documents: List[str],
        context_type: str = "medical",
        top_k: int = 10,
        use_reranking: bool = True
    ) -> List[Tuple[int, float, str]]:
        """
        Perform HyDE-enhanced search on documents
        
        Args:
            query: Search query
            documents: List of documents to search
            context_type: Type of medical context
            top_k: Number of results to return
            use_reranking: Whether to use reranking
        
        Returns:
            List of (doc_index, score, document_text) tuples
        """
        
        # Generate hypothetical answers
        hypotheticals = await self.generate_hypothetical_answer(
            query, context_type, num_hypotheticals=3
        )
        
        # Combine query with hypotheticals
        enhanced_queries = [query] + hypotheticals
        
        # Encode all queries
        query_embeddings = self.embedder.encode(enhanced_queries)
        
        # Average embeddings for final query representation
        combined_embedding = np.mean(query_embeddings, axis=0)
        
        # Encode documents (in production, these would be pre-computed)
        doc_embeddings = self.embedder.encode(documents)
        
        # Perform similarity search
        similarities = np.dot(doc_embeddings, combined_embedding) / (
            np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(combined_embedding)
        )
        
        # Get top-k indices
        if use_reranking:
            # Get more candidates for reranking
            candidate_indices = np.argsort(similarities)[-top_k*3:][::-1]
            
            # Rerank candidates (simplified - would use ColBERT in production)
            reranked = self._rerank_results(
                query, [documents[i] for i in candidate_indices], candidate_indices, similarities
            )
            
            results = reranked[:top_k]
        else:
            # Direct top-k without reranking
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            results = [
                (idx, float(similarities[idx]), documents[idx])
                for idx in top_indices
            ]
        
        return results
    
    def _rerank_results(
        self,
        query: str,
        candidates: List[str],
        indices: List[int],
        initial_scores: np.ndarray
    ) -> List[Tuple[int, float, str]]:
        """
        Rerank results using cross-encoder
        In production, this would use ColBERT or similar
        """
        
        # For now, combine initial scores with length-based heuristic
        # Real implementation would use ColBERT cross-encoder
        
        reranked = []
        for i, (doc, idx) in enumerate(zip(candidates, indices)):
            # Heuristic: boost documents that contain more query terms
            query_terms = set(query.lower().split())
            doc_terms = set(doc.lower().split())
            term_overlap = len(query_terms & doc_terms) / len(query_terms)
            
            # Combine with initial score
            final_score = initial_scores[idx] * 0.7 + term_overlap * 0.3
            
            reranked.append((idx, float(final_score), doc))
        
        # Sort by final score
        reranked.sort(key=lambda x: x[1], reverse=True)
        
        return reranked
    
    async def hybrid_search(
        self,
        query: str,
        documents: List[str],
        context_type: str = "medical",
        top_k: int = 10,
        alpha: float = 0.5
    ) -> List[Tuple[int, float, str]]:
        """
        Perform hybrid search combining HyDE with BM25
        
        Args:
            query: Search query
            documents: List of documents
            context_type: Medical context type
            top_k: Number of results
            alpha: Weight for dense search (1-alpha for sparse)
        
        Returns:
            Combined search results
        """
        
        # Perform HyDE search (dense)
        hyde_results = await self.hyde_search(
            query, documents, context_type, top_k * 2, use_reranking=False
        )
        
        # Perform BM25 search (sparse)
        tokenized_docs = [doc.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Get BM25 top results
        bm25_indices = np.argsort(bm25_scores)[-top_k*2:][::-1]
        bm25_results = [
            (idx, float(bm25_scores[idx]), documents[idx])
            for idx in bm25_indices
        ]
        
        # Normalize scores
        hyde_max = max([s for _, s, _ in hyde_results]) if hyde_results else 1.0
        bm25_max = max([s for _, s, _ in bm25_results]) if bm25_results else 1.0
        
        # Combine results
        combined_scores = {}
        
        for idx, score, doc in hyde_results:
            combined_scores[idx] = alpha * (score / hyde_max)
        
        for idx, score, doc in bm25_results:
            if idx in combined_scores:
                combined_scores[idx] += (1 - alpha) * (score / bm25_max)
            else:
                combined_scores[idx] = (1 - alpha) * (score / bm25_max)
        
        # Sort by combined score
        sorted_results = sorted(
            [(idx, score, documents[idx]) for idx, score in combined_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build FAISS index for efficient similarity search"""
        
        dimension = embeddings.shape[1]
        
        # Use IVF index for larger datasets
        if len(embeddings) > 10000:
            nlist = int(np.sqrt(len(embeddings)))
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            index.train(embeddings)
        else:
            # Use flat index for smaller datasets
            index = faiss.IndexFlatL2(dimension)
        
        index.add(embeddings)
        
        return index
    
    async def medical_context_search(
        self,
        query: str,
        clinical_note: str,
        search_type: str = "medication",
        chunk_size: int = 200,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for specific medical information in clinical notes
        
        Args:
            query: What to search for
            clinical_note: The clinical note to search in
            search_type: Type of search (medication, imaging, labs, etc.)
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        
        Returns:
            List of relevant chunks with metadata
        """
        
        # Chunk the clinical note
        chunks = self._create_medical_chunks(clinical_note, chunk_size, chunk_overlap)
        
        # Perform hybrid search
        results = await self.hybrid_search(
            query=query,
            documents=[c["text"] for c in chunks],
            context_type=search_type,
            top_k=5
        )
        
        # Format results with metadata
        formatted_results = []
        for idx, score, text in results:
            chunk_info = chunks[idx]
            formatted_results.append({
                "text": text,
                "score": score,
                "start_char": chunk_info["start"],
                "end_char": chunk_info["end"],
                "context": self._get_surrounding_context(
                    clinical_note, chunk_info["start"], chunk_info["end"]
                )
            })
        
        return formatted_results
    
    def _create_medical_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[Dict[str, Any]]:
        """Create overlapping chunks of medical text"""
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to end at sentence boundary
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunks.append({
                "text": text[start:end],
                "start": start,
                "end": end
            })
            
            start = end - overlap
        
        return chunks
    
    def _get_surrounding_context(
        self,
        text: str,
        start: int,
        end: int,
        context_chars: int = 100
    ) -> str:
        """Get surrounding context for a chunk"""
        
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        
        # Find sentence boundaries
        if context_start > 0:
            period_before = text.rfind('.', context_start, start)
            if period_before > context_start:
                context_start = period_before + 1
        
        if context_end < len(text):
            period_after = text.find('.', end, context_end)
            if period_after > 0:
                context_end = period_after + 1
        
        return text[context_start:context_end].strip()

# Singleton instance
_hyde_service = None

async def get_hyde_service() -> HyDEService:
    """Get or create HyDE service instance"""
    global _hyde_service
    if _hyde_service is None:
        _hyde_service = HyDEService()
    return _hyde_service