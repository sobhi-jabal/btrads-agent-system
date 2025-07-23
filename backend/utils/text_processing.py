"""Text processing utilities for agent source highlighting"""
import re
from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def find_relevant_sentences(
    text: str,
    query: str,
    embedder: SentenceTransformer,
    top_k: int = 3,
    threshold: float = 0.3
) -> List[Tuple[str, int, int, float]]:
    """
    Find sentences in text most relevant to query using semantic similarity
    
    Returns: List of (sentence_text, start_char, end_char, relevance_score)
    """
    # Tokenize into sentences
    sentences = sent_tokenize(text)
    if not sentences:
        return []
    
    # Track character positions
    sentence_positions = []
    current_pos = 0
    
    for sent in sentences:
        start = text.find(sent, current_pos)
        if start != -1:
            end = start + len(sent)
            sentence_positions.append((sent, start, end))
            current_pos = end
    
    if not sentence_positions:
        return []
    
    # Get embeddings
    query_embedding = embedder.encode(query, convert_to_tensor=True)
    sentence_texts = [s[0] for s in sentence_positions]
    sentence_embeddings = embedder.encode(sentence_texts, convert_to_tensor=True)
    
    # Calculate similarities
    similarities = embedder.similarity(query_embedding, sentence_embeddings)[0]
    
    # Get top-k sentences above threshold
    results = []
    for idx, score in enumerate(similarities):
        if score >= threshold:
            sent_text, start, end = sentence_positions[idx]
            results.append((sent_text, start, end, float(score)))
    
    # Sort by relevance and return top-k
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:top_k]

def calculate_sentence_relevance(
    sentence: str,
    extracted_value: str,
    keywords: List[str] = None
) -> float:
    """
    Calculate relevance of a sentence to an extracted value
    
    Uses keyword matching and string similarity
    """
    sentence_lower = sentence.lower()
    value_lower = str(extracted_value).lower()
    
    # Direct value match
    if value_lower in sentence_lower:
        return 0.9
    
    # Keyword matching
    if keywords:
        keyword_matches = sum(1 for kw in keywords if kw.lower() in sentence_lower)
        if keyword_matches > 0:
            return min(0.8, 0.4 + (keyword_matches * 0.2))
    
    # Partial string matching
    value_words = value_lower.split()
    if len(value_words) > 1:
        word_matches = sum(1 for word in value_words if word in sentence_lower)
        if word_matches > 0:
            return min(0.7, 0.3 + (word_matches / len(value_words) * 0.4))
    
    return 0.2  # Base relevance for being selected

def extract_date_mentions(text: str) -> List[Tuple[str, int, int]]:
    """
    Extract date mentions from text
    
    Returns: List of (date_string, start_char, end_char)
    """
    # Common date patterns
    patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or M/D/YY
        r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}',  # Month DD, YYYY
        r'\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}',     # DD Month YYYY
    ]
    
    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            results.append((match.group(), match.start(), match.end()))
    
    # Remove duplicates and sort by position
    results = list(set(results))
    results.sort(key=lambda x: x[1])
    
    return results

def extract_medication_mentions(text: str) -> List[Tuple[str, str, int, int]]:
    """
    Extract medication mentions from text
    
    Returns: List of (medication_type, mention_text, start_char, end_char)
    """
    medications = {
        'steroids': [
            r'dexamethasone',
            r'decadron',
            r'prednisolone',
            r'prednisone',
            r'steroid[s]?',
            r'corticosteroid[s]?'
        ],
        'avastin': [
            r'avastin',
            r'bevacizumab',
            r'anti[-\s]?angiogenic',
            r'VEGF inhibitor'
        ]
    }
    
    results = []
    for med_type, patterns in medications.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                results.append((med_type, match.group(), match.start(), match.end()))
    
    # Remove duplicates
    results = list(set(results))
    results.sort(key=lambda x: x[2])
    
    return results

def extract_volume_mentions(text: str) -> List[Tuple[str, float, str, int, int]]:
    """
    Extract volume measurements and percentages from text
    
    Returns: List of (type, value, unit, start_char, end_char)
    """
    # Pattern for volume measurements
    volume_pattern = r'(\d+\.?\d*)\s*(mL|ml|cc|cm3|cm³)'
    
    # Pattern for percentage changes
    percent_pattern = r'([+-]?\d+\.?\d*)\s*%'
    
    results = []
    
    # Extract volumes
    for match in re.finditer(volume_pattern, text):
        value = float(match.group(1))
        unit = match.group(2)
        results.append(('volume', value, unit, match.start(), match.end()))
    
    # Extract percentages
    for match in re.finditer(percent_pattern, text):
        value = float(match.group(1))
        results.append(('percentage', value, '%', match.start(), match.end()))
    
    return results

def highlight_in_context(
    text: str,
    start: int,
    end: int,
    context_window: int = 100
) -> Tuple[str, int, int]:
    """
    Get text with surrounding context
    
    Returns: (context_text, highlight_start_in_context, highlight_end_in_context)
    """
    # Calculate context boundaries
    context_start = max(0, start - context_window)
    context_end = min(len(text), end + context_window)
    
    # Extract context
    context_text = text[context_start:context_end]
    
    # Calculate highlight position within context
    highlight_start = start - context_start
    highlight_end = end - context_start
    
    # Add ellipsis if needed
    if context_start > 0:
        context_text = "..." + context_text
        highlight_start += 3
        highlight_end += 3
    
    if context_end < len(text):
        context_text = context_text + "..."
    
    return context_text, highlight_start, highlight_end