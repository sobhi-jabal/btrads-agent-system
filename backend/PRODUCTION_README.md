# BT-RADS Production Backend

## Overview
This is a production-ready BT-RADS backend that uses Ollama for LLM-based medical text extraction. There are no mock or test modes - this is a real application designed for clinical use.

## System Requirements

### Required Dependencies
1. **Ollama** - Must be installed and running
2. **Python 3.8+** with pip
3. **8GB+ RAM** for model loading
4. **10GB+ disk space** for models

### Installation

#### 1. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

#### 2. Start Ollama Service
```bash
ollama serve
```

#### 3. Pull Required Model
```bash
ollama pull phi4:14b
```

#### 4. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 5. Run Setup Script
```bash
./setup_llm.sh
```

## Running the Application

```bash
python btrads_backend.py
```

The backend will start on http://localhost:5001

**Note**: The application will NOT start if Ollama is not running.

## API Usage

### Health Check
```bash
curl http://localhost:5001/health
```

### Extract Information
```bash
curl -X POST http://localhost:5001/api/llm/extract \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_note": "Patient on dexamethasone 4mg daily...",
    "extraction_type": "medications",
    "use_rag": true
  }'
```

## Error Handling

The application returns proper HTTP status codes:

- **400 Bad Request** - Invalid input (missing clinical note, invalid extraction type)
- **500 Internal Server Error** - Processing errors, import errors
- **503 Service Unavailable** - Ollama is not running

## Production Considerations

### Performance
- Models are kept loaded in memory (10-minute timeout)
- RAG reduces context size for faster processing
- Expect 1-3 second response times

### Scaling
- Run multiple instances behind a load balancer
- Use Redis for caching repeated extractions
- Consider GPU acceleration for higher throughput

### Security
- Run behind HTTPS proxy in production
- Implement authentication/authorization
- Audit log all extractions
- Ensure HIPAA compliance for medical data

### Monitoring
- Monitor Ollama service health
- Track extraction success rates
- Alert on high error rates
- Log processing times

## Troubleshooting

### Application Won't Start
```
ERROR: Cannot connect to Ollama service
```
**Solution**: Start Ollama with `ollama serve`

### Model Not Found
```
ERROR: Model phi4:14b not available
```
**Solution**: Pull the model with `ollama pull phi4:14b`

### Out of Memory
```
ERROR: Out of memory
```
**Solution**: 
- Ensure 8GB+ RAM available
- Use smaller model (e.g., mistral:7b)
- Reduce context window size

### Slow Performance
**Solutions**:
- Enable GPU acceleration
- Use SSD for model storage
- Increase system RAM
- Use smaller, faster models

## Support

For issues or questions:
- Check logs in the console output
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Ensure all dependencies installed: `pip list`

## License

This is a medical application. Ensure proper licensing and compliance before clinical use.