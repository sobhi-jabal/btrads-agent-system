"""
RAG retrieval system with FAISS vector store and hybrid search
"""
from typing import List, Dict, Tuple, Optional
import numpy as np
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_processing import smart_medical_chunker, detect_medical_sections


class RAGRetriever:
    """Hybrid retrieval system for medical text"""
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        retriever_type: str = "hybrid"
    ):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.retriever_type = retriever_type
        self.embeddings = None
        
    def _initialize_embeddings(self):
        """Initialize embeddings model"""
        if self.embeddings is None:
            try:
                self.embeddings = SentenceTransformerEmbeddings(model_name=self.embedding_model)
            except Exception as e:
                print(f"Error loading embeddings: {e}")
                return False
        return True
    
    def retrieve_with_source_tracking(
        self,
        text: str,
        query: str,
        use_rag: bool = True,
        max_context_length: int = 2000
    ) -> Tuple[str, List[Dict]]:
        """
        Retrieve relevant context with source tracking
        
        Args:
            text: Full clinical note text
            query: Query for retrieval
            use_rag: Whether to use RAG or return full text
            max_context_length: Maximum context length to return
            
        Returns:
            Tuple of (context_string, source_info_list)
        """
        # Full-report mode
        if not use_rag:
            char_cap = 65_000  # ~16k tokens
            context = text[:char_cap]
            return context, [{
                "chunk_id": -1,
                "section": "full_report",
                "relevance_score": 1.0,
                "source_type": "full_report",
                "content_preview": context[:150] + ("..." if len(context) > 150 else ""),
                "start_pos": 0,
                "end_pos": len(context),
            }]
        
        # RAG mode
        chunks = smart_medical_chunker(text, self.chunk_size, self.chunk_overlap)
        if not chunks:
            return text[:max_context_length], [{"error": "no chunks created"}]
        
        # Build retriever
        retriever = self._build_smart_retriever(chunks)
        if retriever is None:
            # Fallback to first few chunks
            fallback_chunks = chunks[:3]
            context = "\n\n---\n\n".join(c.page_content for c in fallback_chunks)
            return context[:max_context_length], [
                {"chunk_id": i, "error": "retriever failed", "content": c.page_content[:100]}
                for i, c in enumerate(fallback_chunks)
            ]
        
        # Retrieve relevant chunks
        try:
            retrieved = retriever.get_relevant_documents(query)
            if not retrieved:
                retrieved = chunks[:3]  # Fallback
        except Exception as e:
            print(f"Retrieval error: {e}")
            retrieved = chunks[:3]
        
        # Build context and source info
        context_parts = []
        source_info = []
        
        for i, doc in enumerate(retrieved[:5]):  # Limit to top 5
            context_parts.append(doc.page_content)
            source_info.append({
                "chunk_id": doc.metadata.get("chunk_id", i),
                "section": doc.metadata.get("section", "unknown"),
                "relevance_score": doc.metadata.get("relevance_score", 0.5),
                "source_type": doc.metadata.get("source_type", "retrieved"),
                "content_preview": doc.page_content[:150] + "...",
                "start_pos": doc.metadata.get("start_pos", 0),
                "end_pos": doc.metadata.get("end_pos", len(doc.page_content)),
            })
        
        context = "\n\n---\n\n".join(context_parts)
        return context[:max_context_length], source_info
    
    def _build_smart_retriever(self, chunks: List[Document]):
        """Build hybrid retriever with semantic and keyword search"""
        if not self._initialize_embeddings():
            return None
        
        # Build semantic retriever
        try:
            vector_store = FAISS.from_documents(chunks, self.embeddings)
            semantic_retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
        except Exception as e:
            print(f"Vector store creation failed: {e}")
            return None
        
        if self.retriever_type == "semantic":
            return semantic_retriever
        
        # Build keyword retriever
        try:
            keyword_retriever = BM25Retriever.from_documents(chunks, k=5)
        except Exception as e:
            print(f"BM25 creation failed: {e}")
            return semantic_retriever
        
        if self.retriever_type == "keyword":
            return keyword_retriever
        
        # Build ensemble retriever
        try:
            ensemble = EnsembleRetriever(
                retrievers=[semantic_retriever, keyword_retriever],
                weights=[0.6, 0.4]  # Favor semantic search
            )
            return ensemble
        except Exception as e:
            print(f"Ensemble creation failed: {e}")
            return semantic_retriever
    
    def extract_evidence_for_query(
        self,
        text: str,
        query: str,
        max_evidence: int = 5
    ) -> List[Dict]:
        """
        Extract evidence snippets for a specific query
        
        Args:
            text: Clinical note text
            query: Query to find evidence for
            max_evidence: Maximum number of evidence pieces to return
            
        Returns:
            List of evidence dictionaries with positions
        """
        chunks = smart_medical_chunker(text, chunk_size=400, chunk_overlap=100)
        if not chunks:
            return []
        
        retriever = self._build_smart_retriever(chunks)
        if retriever is None:
            return []
        
        try:
            retrieved = retriever.get_relevant_documents(query)[:max_evidence]
        except:
            retrieved = chunks[:max_evidence]
        
        evidence = []
        for doc in retrieved:
            evidence.append({
                "text": doc.page_content,
                "start_pos": doc.metadata.get("start_pos", 0),
                "end_pos": doc.metadata.get("end_pos", len(doc.page_content)),
                "section": doc.metadata.get("section", "unknown"),
                "relevance": doc.metadata.get("relevance_score", 0.5),
                "source": "rag_retrieval"
            })
        
        return evidence


# Singleton instance
_rag_retriever = None

def get_rag_retriever() -> RAGRetriever:
    """Get or create the RAG retriever singleton"""
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever