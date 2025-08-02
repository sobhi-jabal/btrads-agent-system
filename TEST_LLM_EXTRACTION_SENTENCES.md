# Test: LLM Extraction with Source Sentences

## What Was Implemented

We've completely separated LLM extraction from NLP pattern matching and enhanced the LLM to extract exact sentences from the clinical note that support its determinations.

### Changes Made:

1. **Backend Updates**:
   - Updated LLM prompts to request source sentences along with status determinations
   - Modified the JSON output format to include `steroid_evidence` and `avastin_evidence` fields
   - Evidence array now includes the exact sentences extracted by the LLM
   - Removed pattern matching for LLM extraction - now uses only LLM's evidence

2. **Frontend Updates**:
   - Created `LLMExtractionHandler.tsx` with dedicated handlers for LLM results
   - Separated LLM logic from NLP pattern matching in `BTRADSDecisionFlow.tsx`
   - Fixed else block syntax and variable declaration issues
   - Evidence transformation properly handles LLM-extracted sentences

## How to Test

1. **Start the system**:
   ```bash
   docker-compose up
   ```

2. **Go to http://localhost:3001**

3. **Configure extraction**:
   - Click "Extraction Settings"
   - Select "LLM Analysis (Ollama phi4:14b)"

4. **Test Case 1: Clear medication mentions**
   ```
   Patient continues on dexamethasone 4mg daily for vasogenic edema.
   Started Avastin (bevacizumab) infusion on 12/1/2024.
   MRI shows improvement in FLAIR signal.
   ```
   
   **Expected LLM Response**:
   - steroid_status: "stable" or "ongoing"
   - steroid_evidence: "Patient continues on dexamethasone 4mg daily for vasogenic edema."
   - avastin_status: "first_treatment" or "recent"
   - avastin_evidence: "Started Avastin (bevacizumab) infusion on 12/1/2024."

5. **Test Case 2: Complex medication history**
   ```
   Previously on high-dose steroids, now tapered to 2mg daily.
   Completed 6 cycles of Avastin, last dose 3 weeks ago.
   No current anti-angiogenic therapy.
   ```
   
   **Expected LLM Response**:
   - steroid_status: "decreasing" or "tapered"
   - steroid_evidence: "Previously on high-dose steroids, now tapered to 2mg daily."
   - avastin_status: "discontinued" or "completed"
   - avastin_evidence: "Completed 6 cycles of Avastin, last dose 3 weeks ago."

6. **Test Case 3: No medications**
   ```
   Patient not on any steroids or anti-angiogenic therapy.
   Managing symptoms with supportive care only.
   ```
   
   **Expected LLM Response**:
   - steroid_status: "none"
   - steroid_evidence: "Patient not on any steroids or anti-angiogenic therapy."
   - avastin_status: "none"
   - avastin_evidence: "Patient not on any steroids or anti-angiogenic therapy."

## What to Look For

1. **In the Evidence Display**:
   - Evidence items should show the exact sentences from the clinical note
   - Each evidence item should be marked as "LLM extraction"
   - Confidence should be high (95%) for LLM-extracted evidence
   - The sourceText should match the evidence sentences from the LLM

2. **In the Decision Flow**:
   - Reasoning should mention "LLM identified" or "via LLM analysis"
   - Should show the specific status values extracted by LLM
   - Should include "Evidence: [exact sentence]" in the reasoning

3. **In the Console** (if debugging):
   - Check for any errors in the LLM extraction
   - Verify the evidence array contains llm_extracted: true

## Verification Steps

1. The system should NOT fall back to pattern matching when LLM is selected
2. The evidence should contain the exact sentences, not pattern-matched snippets
3. The medication status should reflect what the LLM determined, not hardcoded values
4. No validation UI should appear - extraction should complete automatically

## Troubleshooting

If extraction fails:
1. Check that Ollama is running: `docker ps | grep ollama`
2. Verify phi4 model is available: `docker exec -it ollama ollama list`
3. Check backend logs: `docker logs backend`
4. Ensure OLLAMA_NUM_PARALLEL=1 is set for sequential processing

## Architecture Notes

- LLM extraction is completely separate from NLP pattern matching
- LLM provides both the determination AND the supporting evidence
- Frontend uses dedicated handlers for LLM vs NLP results
- No mixing of extraction methods - each works independently