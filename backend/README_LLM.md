# BT-RADS Backend with Ollama LLM Integration

This backend provides real LLM extraction using Ollama for the BT-RADS system.

## Prerequisites

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

### 2. Start Ollama service
```bash
ollama serve
```

### 3. Pull required models
```bash
# Primary model
ollama pull phi4:14b

# Alternative models (optional)
ollama pull llama3.1:16x17b
ollama pull mistral:7b
```

## Installation

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Ensure Ollama is running:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

## Running the Backend

```bash
python btrads_backend.py
```

The backend will start on http://localhost:5001

## API Endpoints

### LLM Extraction
```
POST /api/llm/extract
```

Request body:
```json
{
  "clinical_note": "Patient clinical note text...",
  "extraction_type": "medications",  // or "radiation_date"
  "use_rag": true  // optional, defaults to true
}
```

Response:
```json
{
  "data": {
    "steroid_status": "increasing",
    "avastin_status": "ongoing"
  },
  "evidence": [...],
  "confidence": 0.95,
  "processing_time": 1.2,
  "method": "llm",
  "model": "phi4:14b",
  "source_tracking": {...}
}
```

## Extraction Types

### 1. Medications
Extracts current medication status:
- **Steroid status**: none, stable, increasing, decreasing, started, unknown
- **Avastin status**: none, ongoing, first_treatment, started, unknown

### 2. Radiation Date
Extracts radiation therapy completion date:
- Returns date in MM/DD/YYYY format or "unknown"

## RAG (Retrieval-Augmented Generation)

The system uses hybrid retrieval combining:
- **Semantic search**: Using sentence-transformers embeddings
- **Keyword search**: Using BM25 algorithm
- **Medical reranking**: Using cross-encoder for relevance

### RAG vs Full Context

- **RAG mode** (`use_rag=true`): Retrieves relevant chunks for focused extraction
- **Full mode** (`use_rag=false`): Sends entire clinical note to LLM

## Error Handling

The system includes multiple fallback mechanisms:
1. **LLM failures**: Falls back to pattern-based extraction
2. **Model unavailable**: Auto-pulls required models
3. **Ollama offline**: Returns HTTP 503 Service Unavailable

## Performance Tips

1. **Keep Ollama running**: Models stay loaded in memory
2. **Use RAG mode**: Faster and more accurate for specific extractions
3. **Batch requests**: Send multiple extraction types together

## Troubleshooting

### Ollama not found
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### Model not available
```bash
# List available models
ollama list

# Pull missing model
ollama pull phi4:14b
```

### Slow performance
- Ensure sufficient RAM (8GB+ recommended)
- Use smaller models for testing (e.g., mistral:7b)
- Enable GPU acceleration if available

## Development

### Adding new extraction types

1. Add prompt to `llm/llm_prompts.py`
2. Update extraction logic in `btrads_backend.py`
3. Add evidence extraction patterns

### Dependencies

Ensure all required packages are installed:
```bash
pip install -r requirements.txt
```