# Test: Extraction Step Display with Clinical Note

## What Was Implemented

The extraction step (start node) now properly displays:
1. The extracted medications and radiation date
2. The full clinical note with highlighted evidence
3. The source sentences that were extracted

## Changes Made

### 1. Updated Start Step Processing
- The 'start' step now collects evidence from extraction results
- Shows extracted medications (steroid_status, avastin_status)
- Shows extracted radiation date
- Includes all evidence items with proper positioning

### 2. Enhanced Step Display for Data Extraction
- When `step.type === 'data-extraction'`, shows special layout
- Two summary cards: one for medications, one for radiation date
- Full clinical note with evidence highlighter below
- Color-coded highlights show where data was extracted from

### 3. Evidence Collection
- Evidence from both LLM and NLP extraction is collected
- Properly transformed with position information for highlighting
- Aggregated into the step for display

## How to Test

1. **Start the System**
   ```bash
   docker-compose up
   ```

2. **Navigate to http://localhost:3001**

3. **Enter Test Clinical Note**:
   ```
   Patient continues on dexamethasone 4mg daily for vasogenic edema.
   Started Avastin (bevacizumab) infusion on 12/1/2024.
   Completed radiation therapy on 10/15/2024.
   MRI shows 30% decrease in FLAIR signal.
   ```

4. **Configure and Start**:
   - Select "LLM Analysis (Ollama phi4:14b)" in extraction settings
   - Click "Start BT-RADS Analysis"

## Expected Results

### In the First Step (Brain Tumor Follow-up)

You should see:

1. **Clinical Assessment Box**:
   - "Successfully extracted key data points from clinical note using LLM analysis. Found X evidence items."

2. **Two Summary Cards**:
   - **Medications Extracted** (blue card):
     - Steroids: `stable` or similar
     - Avastin: `first_treatment` or similar
   - **Radiation Date Extracted** (purple card):
     - Shows: `10/15/2024` or `2024-10-15`

3. **Clinical Note with Extracted Evidence** (below the cards):
   - Full clinical note text displayed
   - "dexamethasone 4mg daily" highlighted in blue
   - "Avastin (bevacizumab) infusion on 12/1/2024" highlighted in blue
   - "radiation therapy on 10/15/2024" highlighted in purple
   - Hover over highlights to see extraction details

## Visual Flow

```
┌─────────────────────────────────────┐
│  Brain Tumor Follow-up              │
│  ✓ Completed → Next: Suitable Prior │
├─────────────────────────────────────┤
│ Clinical Assessment:                │
│ Successfully extracted key data...   │
├─────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────────┐ │
│ │ Medications │ │ Radiation Date  │ │
│ │ Steroids: x │ │ 10/15/2024     │ │
│ │ Avastin: y  │ │                │ │
│ └─────────────┘ └─────────────────┘ │
├─────────────────────────────────────┤
│ Clinical Note with Extracted Evidence│
│ [Highlighted text showing sources]   │
└─────────────────────────────────────┘
```

## Benefits

1. **Immediate Visibility**: Extraction results shown right at the extraction step
2. **Source Verification**: See exactly where each piece of data came from
3. **Clear Process**: Extraction → Display → Continue to BT-RADS flow
4. **Transparency**: Physicians can verify AI extraction accuracy immediately

## Troubleshooting

If evidence doesn't appear:
1. Check that extraction completed successfully
2. Verify evidence array has items with proper position info
3. Ensure clinical note text matches extracted sentences
4. Check browser console for any errors

If highlights don't show:
1. Verify `startIndex` and `endIndex` are not both 0
2. Check that evidence text matches note text
3. Ensure LLM returned source sentences