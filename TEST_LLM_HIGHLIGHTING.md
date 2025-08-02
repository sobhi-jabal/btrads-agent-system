# Test: LLM Evidence Highlighting

## What Was Fixed

The LLM-extracted evidence sentences are now properly highlighted within the clinical note. Previously, the sentences were extracted but not positioned within the original text.

### Implementation Details:

1. **Position Finding Algorithm**:
   - First tries exact match
   - Falls back to case-insensitive match
   - Tries trimmed match (removes leading/trailing whitespace)
   - Finally tries normalized whitespace match (handles multiple spaces/newlines)

2. **Updated Components**:
   - `findSentencePosition()` - Finds the position of extracted sentences
   - `transformLLMEvidence()` - Now accepts clinical note to calculate positions
   - `handleLLMMedications()` - Passes clinical note for position calculation
   - `handleLLMRadiation()` - Passes clinical note for position calculation
   - `BTRADSDecisionFlow` - Provides clinical note to handlers

## How to Test

1. **Start the system**:
   ```bash
   docker-compose up
   ```

2. **Go to http://localhost:3001**

3. **Configure extraction**:
   - Click "Extraction Settings"
   - Select "LLM Analysis (Ollama phi4:14b)"

4. **Test Case 1: Simple sentence matching**
   ```
   Patient continues on dexamethasone 4mg daily for vasogenic edema.
   Started Avastin (bevacizumab) infusion on 12/1/2024.
   MRI shows improvement in FLAIR signal.
   ```
   
   **Expected Behavior**:
   - The sentence "Patient continues on dexamethasone 4mg daily for vasogenic edema." should be highlighted in blue (medication category)
   - The sentence "Started Avastin (bevacizumab) infusion on 12/1/2024." should be highlighted in blue
   - Hover over highlighted text to see confidence and pattern info

5. **Test Case 2: Case variations**
   ```
   PATIENT ON DEXAMETHASONE 4MG DAILY.
   Recently started bevacizumab therapy.
   No evidence of progression.
   ```
   
   **Expected Behavior**:
   - Even if LLM returns lowercase version, highlighting should still work
   - Case-insensitive matching ensures proper highlighting

6. **Test Case 3: Multi-line text**
   ```
   The patient has been on a stable dose of 
   dexamethasone 4mg daily for the past month.
   
   Avastin therapy was initiated on December 1st
   with good tolerance so far.
   ```
   
   **Expected Behavior**:
   - Multi-line sentences should be properly highlighted
   - Whitespace normalization handles line breaks

## Visual Indicators

When working correctly, you should see:

1. **Highlighted Text**: 
   - Blue background for medication evidence
   - Purple background for radiation evidence
   - Yellow background for temporal evidence
   - Opacity varies with confidence (high=100%, medium=75%, low=50%)

2. **Hover Information**:
   - Pattern: "LLM extraction"
   - Confidence: "high"
   - Category: medication/radiation/temporal
   - Reasoning: "Extracted by LLM with 95% confidence"

3. **Evidence Summary**:
   - Shows all extracted evidence items
   - Sorted by relevance score
   - Displays full context

## Troubleshooting

If highlighting doesn't appear:

1. **Check Browser Console**:
   - Look for any JavaScript errors
   - Verify evidence items have non-zero startIndex/endIndex

2. **Check Evidence Data**:
   - In the decision flow, expand the evidence section
   - Verify the evidence items show proper position values

3. **Test Position Finding**:
   - Try simpler sentences first
   - Ensure no special characters are breaking the match

4. **Debug Tips**:
   - The position finder tries multiple strategies
   - If exact match fails, it falls back to increasingly fuzzy matches
   - Console.log can be added to findSentencePosition() for debugging

## Architecture Benefits

- **Separation of Concerns**: LLM focuses on extraction, frontend handles positioning
- **Fallback Strategies**: Multiple matching approaches ensure robustness
- **Maintainability**: Position finding is isolated in one function
- **User Experience**: Visual highlighting provides immediate feedback on what LLM found