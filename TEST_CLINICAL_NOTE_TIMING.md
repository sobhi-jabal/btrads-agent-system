# Test: Clinical Note Panel Timing

## What Changed

The "Complete Clinical Note with All Evidence" panel now appears:
1. **After** the extraction step completes
2. **Only when** there is actual evidence to display
3. **In the correct chronological order** of the workflow

## Previous Behavior (Incorrect)
- Panel appeared immediately after patient header
- Showed even before extraction ran
- Displayed empty when no evidence existed

## New Behavior (Correct)
- Panel appears after ExtractionComparison view
- Only shows when `aggregatedEvidence.length > 0`
- Follows the logical flow: Extract → Show Results → Show Evidence

## How to Test

1. **Start Fresh**
   - Go to http://localhost:3001
   - Enter a clinical note
   - Select LLM extraction mode

2. **Before Starting Analysis**
   - Verify: NO clinical note panel visible
   - Only see: Patient header and input area

3. **Start Analysis**
   - Click "Start BT-RADS Analysis"
   - Watch the workflow progress

4. **After Extraction Step**
   - Once extraction completes, you should see:
     1. Patient Header
     2. Extraction Comparison (if enabled)
     3. **NEW POSITION**: Complete Clinical Note panel
     4. Processing steps below

5. **Verify Evidence**
   - The panel should show:
     - Full clinical note with highlights
     - Evidence summary by category
     - All extracted sentences highlighted

## Test Cases

### Case 1: No Evidence
If extraction finds no evidence:
- Clinical note panel should NOT appear
- Only workflow steps visible

### Case 2: Progressive Evidence
As workflow progresses:
- Evidence accumulates
- Panel updates with new highlights
- Summary shows all categories

### Case 3: New Analysis
Starting a new analysis:
- Previous evidence clears
- Panel disappears until new extraction

## Benefits

1. **Logical Flow**: Evidence appears after extraction, not before
2. **Less Confusion**: No empty panels at start
3. **Clear Causation**: Shows that highlights come FROM extraction
4. **Better UX**: Natural progression of information

## Architecture Note

The panel now checks two conditions:
```javascript
{patientData?.data?.clinical_note && aggregatedEvidence.length > 0 && (
```

This ensures:
- Clinical note exists (patientData check)
- Evidence has been extracted (aggregatedEvidence.length > 0)