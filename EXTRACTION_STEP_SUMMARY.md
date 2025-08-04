# Summary: Extraction Step Display Implementation

## Problem Solved

The user wanted to see the full clinical report with highlighted extracted datapoints at the extraction step, not just at the end of the workflow. Previously:
- Extraction happened invisibly before the workflow
- The 'start' step only showed a truncated note
- No evidence was displayed until after all processing completed

## Solution Implemented

### 1. **Enhanced Start Step**
The 'start' step (type: 'data-extraction') now:
- Collects all evidence from extraction results (medications & radiation date)
- Transforms evidence with proper position information for highlighting
- Passes full clinical note (not truncated) to the display

### 2. **Special Display for Extraction Steps**
Added custom rendering when `step.type === 'data-extraction'`:
- **Two Summary Cards**:
  - Medications card showing steroid_status and avastin_status
  - Radiation date card showing the extracted date
- **Full Clinical Note Panel**:
  - Shows the complete clinical note text
  - Highlights all extracted evidence with color coding
  - Uses the same EvidenceHighlighter component for consistency

### 3. **Evidence Flow**
- Evidence from extraction (LLM or NLP) is collected at the start step
- Each piece of evidence has its position calculated for proper highlighting
- Evidence is displayed immediately in the extraction step
- Also aggregated for the full note display later

## User Experience

Now when the workflow runs:
1. **Extraction happens** (behind the scenes)
2. **Start step shows results** with:
   - What was extracted (medications, dates)
   - Where it came from (highlighted in the note)
   - Clear visual presentation
3. **Workflow continues** with BT-RADS logic

## Key Benefits

1. **Transparency**: Extraction is no longer hidden - users see exactly what was found
2. **Verification**: Physicians can immediately verify extraction accuracy
3. **Context**: Source sentences are highlighted right where they appear
4. **Workflow Integration**: Extraction is now a visible, auditable step in the process

## Technical Notes

- Used existing EvidenceHighlighter component for consistency
- Evidence transformation handles both LLM and NLP extraction
- Position finding ensures highlights appear in the correct location
- Fully integrated with the existing workflow system