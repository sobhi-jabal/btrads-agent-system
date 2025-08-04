# BT-RADS Multi-Agent System - Modernization Guide

This document describes the state-of-the-art modernization of the BT-RADS multi-agent system for 2025.

## Overview

The modernized BT-RADS system features:
- **vLLM Integration**: High-performance local LLM inference with Llama 3.1, Mixtral, and BioMistral
- **LangGraph Orchestration**: Graph-based workflow management for complex BT-RADS decision trees
- **Production-Ready Agents**: Real LLM-powered agents replacing mock implementations
- **Advanced RAG** (coming soon): HyDE + ColBERT for superior medical text retrieval
- **Modern UI** (coming soon): shadcn/ui + Tailwind for professional healthcare interfaces

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                     │
│                  shadcn/ui + React Flow                      │
└─────────────────────────────┬───────────────────────────────┘
                              │ WebSocket
┌─────────────────────────────┴───────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            LangGraph Orchestrator                    │   │
│  │                                                      │   │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ │   │
│  │  │Node│→│Node│→│Node│→│Node│→│Node│→│Node│→│Node│ │   │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────┴───────────────────────────────┐   │
│  │              Specialized Agents                      │   │
│  │  - Prior Assessment    - Medication Status          │   │
│  │  - Imaging Comparison  - Radiation Timeline         │   │
│  │  - Component Analysis  - Extent Analysis            │   │
│  │  - Progression Pattern                              │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────┴───────────────────────────────┐   │
│  │                vLLM Service                          │   │
│  │         Llama 3.1 70B / Mixtral 8x7B                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Set Up vLLM Server

```bash
# Option A: Using Docker (recommended for GPU)
docker-compose -f docker-compose.vllm.yml up -d

# Option B: Using setup script
./scripts/setup_vllm.sh

# Option C: Manual installation
pip install vllm  # or vllm-cpu for CPU-only
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

### 2. Configure Environment

```bash
# Copy example environment
cp .env.example .env

# Edit .env to set:
AGENT_MODE=vllm              # Use vLLM agents (not mock)
ORCHESTRATOR_MODE=langgraph  # Use LangGraph orchestration
VLLM_BASE_URL=http://localhost:8000
```

### 3. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 4. Run the System

```bash
# Terminal 1: Start backend
cd backend
python main.py

# Terminal 2: Start frontend
cd frontend
npm run dev
```

## Key Features

### 1. vLLM Integration

The system uses vLLM for high-performance inference:

- **Automatic Model Selection**: Chooses the best model based on task complexity
- **Continuous Batching**: Processes multiple requests efficiently
- **Quantization Support**: 4-bit and 8-bit quantization for larger models
- **Fallback Logic**: Gracefully falls back to Ollama or mock mode if vLLM unavailable

### 2. LangGraph Orchestration

LangGraph provides superior workflow management:

- **Visual Graph Structure**: BT-RADS flowchart implemented as a stateful graph
- **Checkpointing**: Save and resume processing state
- **Parallel Execution**: Run independent agents concurrently
- **Error Recovery**: Robust error handling with retry logic

### 3. Production Agents

Each agent is specialized for its BT-RADS node:

```python
# Example: Medication Status Agent
class MedicationStatusAgent(VLLMBaseAgent):
    def get_system_prompt(self):
        return """You are a neuro-oncology pharmacist specializing in brain tumor treatments.
        Your expertise includes corticosteroid management and anti-angiogenic therapy..."""
    
    def build_extraction_prompt(self, clinical_note, context):
        # Builds specialized prompt for medication extraction
    
    def validate_extraction(self, extracted_value, context):
        # Validates against medical logic and consistency rules
```

### 4. Advanced Configuration

The system supports multiple deployment modes:

```python
# Agent Modes
AGENT_MODE=vllm     # Production mode with vLLM
AGENT_MODE=ollama   # Alternative with Ollama
AGENT_MODE=mock     # Development/testing mode

# Orchestrator Modes
ORCHESTRATOR_MODE=langgraph  # Graph-based orchestration
ORCHESTRATOR_MODE=simple     # Original simple orchestration
```

## Testing

### Run Integration Tests

```bash
# Test vLLM integration
python tests/test_vllm_integration.py

# Test full pipeline
python tests/test_btrads_pipeline.py

# Load testing
locust -f tests/load_test.py
```

### Verify System Health

```bash
# Check all services
curl http://localhost:8000/health

# Check vLLM
curl http://localhost:8000/v1/models

# Check agent status
curl http://localhost:8000/api/agents/status
```

## Performance Optimization

### vLLM Optimization

```yaml
# docker-compose.vllm.yml
command: >
  --model meta-llama/Meta-Llama-3.1-70B-Instruct
  --tensor-parallel-size 2        # Use 2 GPUs
  --gpu-memory-utilization 0.9    # Use 90% GPU memory
  --max-model-len 8192           # Maximum context length
  --enable-prefix-caching        # Cache common prefixes
```

### Agent Optimization

- **Prompt Caching**: Common prompts are cached
- **Batch Processing**: Multiple patients processed in parallel
- **Result Caching**: Cache extraction results with Redis
- **Embedding Cache**: Reuse embeddings for source highlighting

## Monitoring

The system includes comprehensive monitoring:

- **OpenTelemetry**: Distributed tracing for all operations
- **Prometheus Metrics**: Performance and usage metrics
- **Structured Logging**: JSON logs with correlation IDs
- **Health Checks**: Automatic service health monitoring

## Security

- **API Key Authentication**: Secure vLLM endpoints
- **HIPAA Compliance**: Patient data encryption
- **Audit Trail**: Complete history of all decisions
- **Role-Based Access**: Different permissions for users

## Troubleshooting

### vLLM Issues

```bash
# Check vLLM logs
docker logs btrads-vllm

# Test vLLM directly
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "meta-llama/Meta-Llama-3.1-8B-Instruct", 
       "messages": [{"role": "user", "content": "Hello"}]}'
```

### Agent Issues

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check agent initialization
python -c "from config.agent_config import agent_config; print(agent_config.mode)"
```

### Performance Issues

- Reduce model size (70B → 8B)
- Enable quantization (4-bit/8-bit)
- Use CPU mode for development
- Adjust batch sizes

## Next Steps

1. **Implement HyDE + ColBERT RAG** for better retrieval
2. **Add shadcn/ui components** for modern UI
3. **Implement predictive dashboards** with real-time updates
4. **Add clinical decision support** features
5. **Build comprehensive audit trail** visualization

## Contributing

See CONTRIBUTING.md for development guidelines.

## License

This project is licensed under the MIT License.