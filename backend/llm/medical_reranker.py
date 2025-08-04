"""
Medical document reranker using cross-encoder models
"""
from typing import List, Tuple, Sequence, Optional
from langchain.schema import Document
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from langchain.callbacks.manager import Callbacks
from sentence_transformers import CrossEncoder


class MedicalReranker(BaseDocumentCompressor):
    """
    Rerank documents using a cross-encoder model for medical relevance
    """
    model_name: str = "BAAI/bge-reranker-v2-m3"
    top_n: int = 3
    model: Optional[CrossEncoder] = None
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", top_n: int = 3):
        super().__init__()
        self.model_name = model_name
        self.top_n = top_n
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the cross-encoder model"""
        try:
            self.model = CrossEncoder(self.model_name)
        except Exception as e:
            print(f"Warning: Cross-encoder model unavailable - {e}")
            self.model = None
    
    class Config:
        extra = "forbid"
        arbitrary_types_allowed = True
    
    def medical_rerank(self, query: str, documents: List[str]) -> List[Tuple[int, float]]:
        """
        Rerank documents based on relevance to query
        
        Args:
            query: Query string
            documents: List of document strings
            
        Returns:
            List of (index, score) tuples sorted by relevance
        """
        if self.model is None:
            # Fallback: return top N with default scores
            return [(i, 0.5) for i in range(min(len(documents), self.top_n))]
        
        # Prepare pairs for cross-encoder
        pairs = [[query, doc] for doc in documents]
        
        # Get relevance scores
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            print(f"Reranking error: {e}")
            return [(i, 0.5) for i in range(min(len(documents), self.top_n))]
        
        # Sort by score (descending)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        
        # Return top N
        return ranked[:self.top_n]
    
    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Compress documents by reranking and selecting top N
        
        Args:
            documents: Input documents
            query: Query for relevance scoring
            callbacks: Optional callbacks
            
        Returns:
            Top N most relevant documents with relevance scores
        """
        if not documents:
            return []
        
        # Extract text content
        doc_texts = [doc.page_content for doc in documents]
        
        # Rerank
        ranked_indices = self.medical_rerank(query, doc_texts)
        
        # Build output with relevance scores
        output = []
        for idx, score in ranked_indices:
            doc = documents[idx]
            # Add relevance score to metadata
            doc.metadata["relevance_score"] = float(score)
            output.append(doc)
        
        return output
    
    async def acompress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """Async version - just calls sync version"""
        return self.compress_documents(documents, query, callbacks)


def create_reranked_retriever(base_retriever, top_n: int = 3):
    """
    Create a retriever with medical reranking
    
    Args:
        base_retriever: Base retriever to wrap
        top_n: Number of documents to keep after reranking
        
    Returns:
        ContextualCompressionRetriever with medical reranking
    """
    from langchain.retrievers import ContextualCompressionRetriever
    
    reranker = MedicalReranker(top_n=top_n)
    return ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever
    )