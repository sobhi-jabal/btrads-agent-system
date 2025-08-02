"""
LLM prompt templates for BT-RADS extraction
Ported from btrads_main_old.py with enhancements
"""

# Medication extraction prompt configuration
MEDICATION_PROMPT = {
    "system_message": "You are an expert medical data extractor specializing in brain tumor patient medication management.",
    "instruction": """Extract CURRENT medication status from the clinical note with high precision.

STEROID STATUS - Look for dexamethasone, decadron, prednisolone, prednisone:
- 'none': Patient is not currently on steroids
- 'stable': Patient continues on same steroid dose  
- 'increasing': Steroid dose being increased/escalated
- 'decreasing': Steroid dose being tapered/decreased
- 'started': Patient newly started on steroids
- 'unknown': Cannot determine from available information

AVASTIN STATUS - Look for Avastin, bevacizumab, BV, anti-angiogenic therapy:
- 'none': Patient is not on Avastin therapy
- 'ongoing': Patient continuing established Avastin therapy
- 'first_treatment': This is clearly the patient's first Avastin dose/cycle
- 'started': Recently started Avastin therapy  
- 'unknown': Cannot determine from available information

Focus on CURRENT status only. Be conservative - use 'unknown' if uncertain.

Return ONLY: {"steroid_status": "X", "avastin_status": "Y"}""",
    "output_format": "json",
    "json_key": "medication_status",
    "few_shots": [
        {
            "role": "user",
            "content": "Current Medications: Dexamethasone 4mg daily (increased from 2mg last week)"
        },
        {
            "role": "assistant", 
            "content": '{"steroid_status": "increasing", "avastin_status": "none"}'
        },
        {
            "role": "user",
            "content": "Treatment plan: Continue Avastin 10mg/kg IV q2 weeks. Third cycle today."
        },
        {
            "role": "assistant",
            "content": '{"steroid_status": "unknown", "avastin_status": "ongoing"}'
        }
    ]
}

# Radiation date extraction prompt configuration
RADIATION_DATE_PROMPT = {
    "system_message": "You are an expert medical data extractor specializing in brain tumor treatment timelines.",
    "instruction": """Find when this patient completed their most recent radiation therapy course.

Look for: radiation therapy completion, end of XRT, chemoradiation finished, last radiation dose.

Be precise about COMPLETION date, not start date.

Return ONLY: {"radiation_date": "MM/DD/YYYY"} or {"radiation_date": "unknown"}""",
    "output_format": "json",
    "json_key": "radiation_date",
    "few_shots": [
        {
            "role": "user",
            "content": "Completed concurrent chemoradiation on 5/15/2023. Started temozolomide maintenance."
        },
        {
            "role": "assistant",
            "content": '{"radiation_date": "5/15/2023"}'
        },
        {
            "role": "user", 
            "content": "History: Brain tumor diagnosed 2022. Multiple surgeries. No radiation mentioned."
        },
        {
            "role": "assistant",
            "content": '{"radiation_date": "unknown"}'
        }
    ]
}

# BT-RADS flowchart node prompts
BTRADS_NODE_PROMPTS = {
    # Node 1: Suitable Prior
    "suitable_prior": {
        "system_message": "You are a neuroradiology expert applying BT-RADS criteria for brain tumor follow-up.",
        "instruction": """Determine if there is a suitable prior imaging study for BT-RADS comparison.

BT-RADS requires a baseline study for comparison. Look for:
- References to prior MRI scans
- Comparison statements  
- Baseline post-operative imaging
- Previous follow-up studies

If no clear evidence of prior imaging is found, return "unknown".

Return ONLY: {"available": "yes/no/unknown", "reasoning": "brief explanation of prior imaging availability or information limitation"}""",
        "output_format": "json",
        "json_key": "suitable_prior",
    },

    # Node 2: Imaging Assessment
    "imaging_assessment": {
        "system_message": "You are a neuroradiology expert applying BT-RADS imaging assessment criteria using quantitative volume data.",
        "instruction": """Compare current imaging with prior using BT-RADS criteria and provided volume data.

CRITICAL: Volume Percentage Interpretation:
- NEGATIVE percentage (-X%) = DECREASED volume = IMPROVEMENT
- POSITIVE percentage (+X%) = INCREASED volume = WORSENING  
- Values near 0% (±10%) = STABLE

CLINICAL SIGNIFICANCE RULE: 
- 1 ml absolute change = 1 x 1 x 1 cm = measurable disease
- Changes < 1 ml are NOT clinically significant, even if >10% percentage change
- Always consider both percentage AND absolute volume changes

MIXED PATTERN RULE: When FLAIR and enhancement change in opposite directions, ALWAYS prioritize the enhancement change.

DECISION LOGIC:
- Both decreased (negative %) -> "improved"
- Both stable (±10%) -> "unchanged" 
- Either shows significant increase (>+10% positive) -> "worse"
- Mixed pattern -> Follow enhancement direction

Examples:
- FLAIR -48%, ENH -25% -> "improved" (both decreased)
- FLAIR +9%, ENH +790% -> "worse" (enhancement dominates)
- FLAIR +15%, ENH -5% -> "unchanged" (enhancement priority: -5% = stable)
- Small volume: 0.5 ml change with 50% increase -> "unchanged" (absolute change < 1 ml)

If volume data is missing or unclear, return "unknown".

Return ONLY: {"assessment": "improved/unchanged/worse/unknown", "reasoning": "volume changes with enhancement priority rule applied or data limitation noted"}""",
        "output_format": "json",
        "json_key": "imaging_assessment",
    },

    # Node 3A: Medication Effects
    "on_medications": {
        "system_message": "You are a neuroradiology expert applying BT-RADS medication effect criteria for improved imaging.",
        "instruction": """For IMPROVED imaging per BT-RADS, determine which medications could explain the improvement.

BT-RADS specifically considers these medication effects:
- **Avastin (bevacizumab)**: Anti-angiogenic therapy can cause rapid improvement in enhancement 
- **Increasing steroids**: Steroid dose increases can reduce edema and mass effect
- **Neither**: No relevant medication effects identified

Check current medication status and recent changes that correlate with imaging timeline.

BT-RADS decision tree:
- If on Avastin -> evaluate response type (Node 3B)
- If increasing steroids -> evaluate steroid effect timing
- If neither -> true tumor improvement (BT-1a)

If medication status cannot be determined, return "unknown".

Return ONLY: {"on_medications": "avastin/increasing_steroids/neither/unknown", "reasoning": "medication status and temporal correlation with improvement or information limitation"}""",
        "output_format": "json",
        "json_key": "on_medications",
    },

    # Node 3B: Avastin Response
    "avastin_response": {
        "system_message": "You are a neuroradiology expert applying BT-RADS Avastin response criteria using volume patterns.",
        "instruction": """For patients on Avastin with improved imaging, determine BT-RADS response type.

BT-RADS Avastin Response Categories:
- **BOTH decreased**: Both FLAIR and enhancement decreased -> favorable response (BT-1a)
- **ONLY enhancement decreased**: Enhancement decreased but FLAIR stable/increased -> typical Avastin effect (BT-1b)

The distinction is critical:
- BT-1a suggests true tumor response
- BT-1b suggests medication effect only

If volume patterns are unclear, return "unknown".

Return ONLY: {"response_type": "both_decreased/only_enhancement_decreased/unknown", "reasoning": "specific volume changes observed or data limitation"}""",
        "output_format": "json",
        "json_key": "avastin_response",
    }
}

# Combined prompts dictionary
ALL_PROMPTS = {
    "medications": MEDICATION_PROMPT,
    "radiation_date": RADIATION_DATE_PROMPT,
    **BTRADS_NODE_PROMPTS
}