# Docker Setup Instructions

## Quick Start

1. **Build and start all services:**
   ```bash
   make build
   make start
   ```

2. **Download phi4 model (first time only):**
   ```bash
   make setup-models
   ```

3. **Check logs:**
   ```bash
   make logs
   ```

## Testing Ollama with Phi4

1. **Check if Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Test phi4 extraction:**
   ```bash
   curl -X POST http://localhost:8001/api/llm/extract \
     -H "Content-Type: application/json" \
     -d '{
       "clinical_note": "Patient on dexamethasone 4mg daily. Completed radiation therapy on 10/15/2024.",
       "extraction_type": "medications",
       "model": "phi4:14b"
     }'
   ```

## Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- Ollama: http://localhost:11434

## Extraction Modes

1. **NLP Mode**: Fast pattern-based extraction
2. **LLM Mode**: Uses Ollama with phi4 model (no fallbacks)
3. **Both Mode**: Runs both methods independently

## Important Notes

- No fallbacks: If LLM mode is selected and Ollama fails, an error will be shown
- Sequential processing: Ollama is configured to process one request at a time
- Timeout: 2 minutes for phi4 extraction

## Troubleshooting

1. **If Ollama is slow:**
   - Ensure phi4 model is downloaded: `make setup-models`
   - Check Ollama logs: `make ollama-logs`
   - Verify model is loaded: `curl http://localhost:11434/api/tags`

2. **If extraction fails:**
   - Check backend logs: `make backend-logs`
   - Ensure Ollama is healthy: `docker-compose ps`
   - Try a simple Ollama test: `make test-ollama`

## Stop Services

```bash
make stop
```

## Clean Everything

```bash
make clean
```