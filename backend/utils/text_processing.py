"""Text processing utilities for agent source highlighting"""
import re
from typing import List, Tuple, Dict, Any
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

def detect_medical_sections(text: str) -> List[Tuple[str, int, int]]:
    """
    Detect medical document sections in text
    Returns: List of (section_name, start_pos, end_pos)
    """
    patterns = [
        (r"Oncology Treatment History:", "treatment_history"),
        (r"Current Medications:", "current_medications"),
        (r"Treatment to be received:", "treatment_plan"),
        (r"History of Present Illness:", "present_illness"),
        (r"Assessment & Plan:", "assessment_plan"),
        (r"Subjective:", "subjective"),
        (r"Objective:", "objective"),
        (r"Past Medical History:", "past_medical"),
        (r"Past Surgical History:", "past_surgical"),
        (r"Social History:", "social_history"),
        (r"Review of Systems:", "review_systems"),
        (r"Physical Exam:", "physical_exam"),
        (r"Laboratory:", "laboratory"),
        (r"Allergies:", "allergies"),
        (r"Impression:", "impression"),
        (r"Imaging:", "imaging"),
        (r"Medications:", "medications"),
        (r"Chief Complaint:", "chief_complaint"),
    ]
    
    sections: List[Tuple[str, int, int]] = []
    
    # Find all section headers
    for pat, name in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            sections.append((name, m.start(), m.end()))
    
    # Sort by position
    sections.sort(key=lambda x: x[1])
    
    # Determine section boundaries
    final_sections: List[Tuple[str, int, int]] = []
    for i, (name, start, header_end) in enumerate(sections):
        # End position is either start of next section or end of text
        end = sections[i + 1][1] if i < len(sections) - 1 else len(text)
        final_sections.append((name, start, end))
    
    return final_sections

def smart_medical_chunker(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Smart medical text chunking that preserves section boundaries
    Returns: List of chunks with metadata
    """
    # Clean text
    cleaned = minimal_clean_text(text)
    
    # Detect sections
    sections = detect_medical_sections(cleaned)
    
    chunks: List[Dict[str, Any]] = []
    chunk_id = 0
    
    if not sections:
        # No sections found - fall back to regular chunking
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", ".", " "],
        )
        
        for i, chunk_text in enumerate(splitter.split_text(cleaned)):
            # Find position in original text
            start_pos = cleaned.find(chunk_text)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "chunk_id": i,
                    "section": "unknown",
                    "start_pos": start_pos,
                    "end_pos": start_pos + len(chunk_text) if start_pos != -1 else -1,
                    "source_type": "regular_chunk",
                }
            })
        return chunks
    
    # Process each section
    for name, start, end in sections:
        section_text = cleaned[start:end]
        
        if len(section_text) <= chunk_size:
            # Section fits in one chunk
            chunks.append({
                "text": section_text,
                "metadata": {
                    "chunk_id": chunk_id,
                    "section": name,
                    "start_pos": start,
                    "end_pos": end,
                    "source_type": "section_chunk",
                }
            })
            chunk_id += 1
        else:
            # Section needs to be split
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", ".", " "],
            )
            
            for i, sub_chunk in enumerate(splitter.split_text(section_text)):
                # Calculate position within section
                sub_start = section_text.find(sub_chunk)
                actual_start = start + sub_start if sub_start != -1 else start
                
                chunks.append({
                    "text": sub_chunk,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "section": name,
                        "section_part": i,
                        "start_pos": actual_start,
                        "end_pos": actual_start + len(sub_chunk),
                        "source_type": "section_subchunk",
                    }
                })
                chunk_id += 1
    
    return chunks

def minimal_clean_text(text: str) -> str:
    """
    Minimal text cleaning to preserve medical information
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Replace smart quotes and special characters
    text = (
        text.replace('"', '"')
        .replace('"', '"')
        .replace("'", "'")
        .replace("'", "'")
        .replace("–", "-")
        .replace("—", "-")
        .replace("…", "...")
    )
    
    # Remove non-printable characters except newlines, tabs
    text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\t\r")
    
    # Normalize excessive newlines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    
    return text.strip()

def extract_evidence_with_positions(
    text: str,
    extraction_type: str,
    extracted_values: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Extract evidence for LLM extraction with character positions
    """
    evidence = []
    
    if extraction_type == "medications":
        # Extract medication evidence
        med_mentions = extract_medication_mentions(text)
        
        for med_type, mention, start, end in med_mentions:
            # Get context around mention
            context, ctx_start, ctx_end = highlight_in_context(text, start, end, 100)
            
            evidence.append({
                "type": med_type,
                "text": context,
                "mention": mention,
                "start_pos": start,
                "end_pos": end,
                "context_start": ctx_start,
                "context_end": ctx_end,
                "relevance": 0.9,
                "source": "pattern_match"
            })
    
    elif extraction_type == "radiation_date":
        # Extract date evidence
        date_mentions = extract_date_mentions(text)
        
        # Look for radiation-related context
        radiation_keywords = ["radiation", "xrt", "rt", "radiotherapy", "irradiation"]
        
        for date_str, start, end in date_mentions:
            # Check if radiation keyword nearby
            context_start = max(0, start - 200)
            context_end = min(len(text), end + 200)
            context = text[context_start:context_end].lower()
            
            relevance = 0.5  # Base relevance for any date
            for keyword in radiation_keywords:
                if keyword in context:
                    relevance = 0.9
                    break
            
            # Get display context
            display_context, ctx_start, ctx_end = highlight_in_context(text, start, end, 100)
            
            evidence.append({
                "type": "radiation_date",
                "text": display_context,
                "date": date_str,
                "start_pos": start,
                "end_pos": end,
                "context_start": ctx_start,
                "context_end": ctx_end,
                "relevance": relevance,
                "source": "pattern_match"
            })
    
    # Sort by relevance
    evidence.sort(key=lambda x: x["relevance"], reverse=True)
    
    return evidence[:5]  # Return top 5 evidence items