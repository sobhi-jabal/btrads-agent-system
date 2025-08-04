# Testing the BT-RADS System with Phi4 LLM Extraction

## Current Setup
- **Backend**: Running on http://localhost:8001
- **Frontend**: Running on http://localhost:3001
- **Ollama**: Running on http://localhost:11434 with phi4:14b model

## Test Steps

1. **Open the Application**
   - Go to http://localhost:3001
   
2. **Configure Extraction Settings**
   - Click on "Extraction Settings" section
   - Select "LLM Analysis (Ollama phi4:14b)"
   - You should see "Current selection: LLM Analysis"

3. **Test Clinical Note**
   - Click on "Clinical Note Analysis" section
   - Enter this test note:
   ```
   Patient on dexamethasone 4mg daily. Completed radiation therapy on 10/15/2024.
   FLAIR signal increased by 15% compared to baseline.
   Enhancement decreased by 8% from prior scan.
   ```

4. **Start Analysis**
   - Click "Start BT-RADS Analysis"
   - The system will:
     - Use Ollama with phi4 for extraction (takes ~20-30 seconds)
     - Extract medication status: steroid = stable
     - Extract radiation date: 10/15/2024
     - Proceed through the BT-RADS flowchart

## Expected Behavior
- **No fallbacks**: If Ollama fails, you'll see an error
- **Sequential processing**: One request at a time
- **Phi4 extraction**: Takes 20-30 seconds but provides accurate results

## Current Status
✅ Backend API working with phi4
✅ Ollama configured for sequential processing
✅ Frontend updated to remove fallbacks
✅ Timeout set to 120 seconds for phi4

## API Test
You can test the extraction API directly:
```bash
curl -X POST http://localhost:8001/api/llm/extract \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_note": "Patient on dexamethasone 4mg daily.",
    "extraction_type": "medications",
    "model": "phi4:14b"
  }'
```

Response time: ~21 seconds