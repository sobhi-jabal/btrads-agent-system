# BT-RADS System Validation Modes

## Overview

The BT-RADS system supports two validation modes for processing patient data:
1. **Auto-Validation Mode** - LLM extractions are automatically accepted
2. **Manual Validation Mode** - Each extraction requires clinician review

## Current Behavior

As of the latest update:
- **Default mode**: AUTO (changed from manual)
- **Configurable via**: Environment variable or API parameter

## Configuration Options

### 1. Environment Variable (Default Setting)
```bash
# In .env file
DEFAULT_VALIDATION_MODE=auto  # or manual
```

### 2. API Parameter
```bash
# Auto-validate mode (automatic acceptance)
curl -X POST "http://localhost:8000/api/patients/{patient_id}/process?auto_validate=true"

# Manual validation mode (requires review)
curl -X POST "http://localhost:8000/api/patients/{patient_id}/process?auto_validate=false"

# Use default from environment
curl -X POST "http://localhost:8000/api/patients/{patient_id}/process"
```

## How Each Mode Works

### Auto-Validation Mode (`auto_validate=true`)
1. Patient data is processed through the BT-RADS flowchart
2. Each agent extracts information using the LLM
3. Extractions are **automatically accepted**
4. Processing continues without pausing
5. Final BT-RADS score is generated immediately

**Use when**:
- Testing the system
- Processing large batches
- High confidence in LLM accuracy
- Non-critical applications

### Manual Validation Mode (`auto_validate=false`)
1. Patient data is processed through the BT-RADS flowchart
2. Each agent extracts information using the LLM
3. System **pauses** and shows extraction results in UI
4. Clinician reviews and can:
   - Accept the extraction as-is
   - Modify the values
   - Add clinical notes
5. Processing continues after validation
6. Final BT-RADS score reflects validated values

**Use when**:
- Clinical production use
- Quality assurance needed
- Training/educational purposes
- Critical decision making

## What You're Seeing

When you see the validation UI with:
- "On Medications?"
- Evidence found
- Dropdown selections

This means the system is in **manual validation mode** and is:
1. Showing you what the LLM extracted
2. Waiting for your confirmation/correction
3. Will not proceed until you validate

## Testing LLM Extraction

To verify the LLM is working without the validation UI:

### Option 1: Use Test Script
```bash
cd backend
python test_llm_extraction.py
```

This will show you raw LLM output without any UI.

### Option 2: Enable Auto-Validation
```bash
# Set in .env
DEFAULT_VALIDATION_MODE=auto

# Or use API parameter
?auto_validate=true
```

### Option 3: Check Backend Logs
```bash
# Watch for LLM calls in logs
tail -f backend.log | grep -E "vllm|extract|confidence"
```

## Troubleshooting

### "Why am I seeing the validation UI?"
- Check if `auto_validate=false` or not specified
- Check `DEFAULT_VALIDATION_MODE` in .env
- The system defaults to manual if not specified

### "Is the LLM actually working?"
- Check backend logs for extraction details
- Run `test_llm_extraction.py`
- Look for `processing_time_ms` and `llm_model` in responses
- Check if vLLM/Ollama services are running

### "How do I skip validation?"
- Set `DEFAULT_VALIDATION_MODE=auto` in .env
- Pass `?auto_validate=true` in API calls
- Use the test scripts for direct extraction

## Best Practices

1. **Development**: Use auto-validation for faster iteration
2. **Production**: Use manual validation for safety
3. **Testing**: Mix both modes to verify accuracy
4. **Training**: Use manual mode to understand system behavior

## Technical Details

The validation flow is controlled in:
- `api/routes/patients.py`: API endpoint defaults
- `agents/orchestration/agent_orchestrator.py`: Line 136 checks validation mode
- `frontend/components/validation/ValidationDialog.tsx`: UI component

When `auto_validate=false`, the system:
1. Runs the agent extraction
2. Sends `validation_required` WebSocket event
3. Waits for `validate_result` call
4. Continues processing after validation