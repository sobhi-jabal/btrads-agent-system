# Fix: ReferenceError for originalNote

## Problem
The error occurred in the `node_4_time_since_xrt` case where the code tried to use `originalNote` variable that wasn't defined in that scope:

```
ReferenceError: Can't find variable: originalNote
```

This happened at line 1221:
```javascript
radEvidence = transformEvidence(extraction.nlp.radiationDate.evidence || [], originalNote)
```

## Root Cause
- Each case block in the switch statement has its own scope
- `originalNote` was defined in `node_3a_medications` case but not in `node_4_time_since_xrt`
- When NLP extraction tried to transform evidence, it couldn't find the variable

## Solution
Added the definition of `originalNote` at the beginning of the `node_4_time_since_xrt` case:

```javascript
case 'node_4_time_since_xrt': {
  // Define originalNote for this scope
  const originalNote = patient?.data?.clinical_note || ''
  
  // Rest of the code...
}
```

## Result
- The variable is now properly defined before it's used
- Evidence transformation will work correctly for NLP extraction
- The red exclamation mark error should be resolved

## Testing
To verify the fix:
1. Use NLP extraction mode
2. Process a clinical note with radiation date
3. The workflow should progress past the "Time Since XRT" step without errors
4. Evidence should be properly highlighted