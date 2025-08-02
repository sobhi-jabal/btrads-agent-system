/**
 * Consistency validation functions for BT-RADS processing
 * Based on the validation logic from btrads_main_old.py
 */

interface ValidationResult {
  isValid: boolean
  issues: string[]
  corrections: Record<string, any>
  warnings: string[]
}

interface BTRADSResult {
  steroid_status?: string
  avastin_status?: string
  on_medications?: string
  algorithm_path?: string
  imaging_assessment?: string
  flair_change_pct?: number
  enhancement_change_pct?: number
  bt_rads_score?: string
  [key: string]: any
}

/**
 * Validate and fix medication consistency between status and algorithm decisions
 */
export function validateMedicationConsistency(result: BTRADSResult): ValidationResult {
  const validation: ValidationResult = {
    isValid: true,
    issues: [],
    corrections: {},
    warnings: []
  }

  // Fix Avastin inconsistencies
  if (result.on_medications === 'avastin' && result.avastin_status === 'unknown') {
    validation.issues.push('Algorithm found Avastin but status was unknown')
    
    // Auto-correct based on algorithm decision
    if (result.algorithm_path?.includes('FIRST')) {
      validation.corrections.avastin_status = 'first_treatment'
    } else if (result.algorithm_path?.includes('SUSTAINED')) {
      validation.corrections.avastin_status = 'ongoing'
    } else {
      validation.corrections.avastin_status = 'started'
    }
    
    validation.warnings.push(`Auto-corrected avastin_status to: ${validation.corrections.avastin_status}`)
  }

  // Fix steroid inconsistencies
  if (result.on_medications === 'increasing_steroids' && result.steroid_status === 'unknown') {
    validation.issues.push('Algorithm found increasing steroids but status was unknown')
    validation.corrections.steroid_status = 'increasing'
    validation.warnings.push('Auto-corrected steroid_status to: increasing')
  }

  // Check for logical inconsistencies
  if (result.on_medications === 'none' && 
      (result.steroid_status !== 'none' && result.steroid_status !== 'unknown') ||
      (result.avastin_status !== 'none' && result.avastin_status !== 'unknown')) {
    validation.issues.push('Medication status inconsistency: on_medications is none but medications detected')
    validation.isValid = false
  }

  return validation
}

/**
 * Apply enhancement priority rule for mixed volume patterns
 * When FLAIR and enhancement show opposite changes, prioritize enhancement
 */
export function applyEnhancementPriorityRule(
  flairChange: number | string,
  enhChange: number | string,
  baselineFlair?: number,
  baselineEnh?: number,
  followupFlair?: number,
  followupEnh?: number
): { assessment: string; reasoning: string } {
  // Parse values
  let flairVal: number
  let enhVal: number
  
  try {
    flairVal = typeof flairChange === 'string' ? parseFloat(flairChange) : flairChange
    enhVal = typeof enhChange === 'string' ? parseFloat(enhChange) : enhChange
  } catch {
    return {
      assessment: 'unknown',
      reasoning: 'Cannot parse volume changes'
    }
  }

  // Calculate absolute volume changes if data available
  let flairAbsChange: number | null = null
  let enhAbsChange: number | null = null
  
  if (baselineFlair !== undefined && followupFlair !== undefined) {
    try {
      const baselineFlairVol = Number(baselineFlair)
      const followupFlairVol = Number(followupFlair)
      flairAbsChange = followupFlairVol - baselineFlairVol
    } catch {
      // Ignore parsing errors
    }
  }
  
  if (baselineEnh !== undefined && followupEnh !== undefined) {
    try {
      const baselineEnhVol = Number(baselineEnh)
      const followupEnhVol = Number(followupEnh)
      enhAbsChange = followupEnhVol - baselineEnhVol
    } catch {
      // Ignore parsing errors
    }
  }

  // Define significant change threshold (±10%)
  const STABILITY_THRESHOLD = 10
  
  // Categorize changes
  const flairCategory = Math.abs(flairVal) <= STABILITY_THRESHOLD ? 'stable' :
                       flairVal < 0 ? 'improved' : 'worse'
  const enhCategory = Math.abs(enhVal) <= STABILITY_THRESHOLD ? 'stable' :
                     enhVal < 0 ? 'improved' : 'worse'

  // Mixed pattern detection
  if (flairCategory !== enhCategory && 
      flairCategory !== 'stable' && 
      enhCategory !== 'stable') {
    // Mixed pattern - apply enhancement priority rule
    let reasoning = `MIXED PATTERN DETECTED - Enhancement Priority Rule Applied. `
    reasoning += `FLAIR ${flairCategory} (${flairVal}%), Enhancement ${enhCategory} (${enhVal}%). `
    
    if (flairAbsChange !== null && enhAbsChange !== null) {
      reasoning += `Absolute changes: FLAIR ${flairAbsChange.toFixed(1)}mL, Enhancement ${enhAbsChange.toFixed(1)}mL. `
    }
    
    reasoning += `Following enhancement change for overall assessment.`
    
    return {
      assessment: enhCategory,
      reasoning
    }
  }

  // Concordant or single change pattern
  if (flairCategory === 'worse' || enhCategory === 'worse') {
    return {
      assessment: 'worse',
      reasoning: `FLAIR ${flairVal}%, ENH ${enhVal}% - progression detected`
    }
  } else if (flairCategory === 'improved' || enhCategory === 'improved') {
    return {
      assessment: 'improved',
      reasoning: `FLAIR ${flairVal}%, ENH ${enhVal}% - improvement detected`
    }
  } else {
    return {
      assessment: 'unchanged',
      reasoning: `FLAIR ${flairVal}%, ENH ${enhVal}% - stable changes`
    }
  }
}

/**
 * Cross-validate volume-based assessment with LLM assessment
 */
export function crossValidateAssessments(
  volumeAssessment: string,
  llmAssessment: string,
  volumeReasoning: string
): { 
  finalAssessment: string
  validationNote: string
  confidence: 'high' | 'medium' | 'low'
} {
  if (volumeAssessment === 'unknown') {
    return {
      finalAssessment: llmAssessment,
      validationNote: 'Using LLM assessment (no volume data)',
      confidence: 'medium'
    }
  }

  if (llmAssessment === 'unknown') {
    return {
      finalAssessment: volumeAssessment,
      validationNote: 'Using volume-based assessment (LLM uncertain)',
      confidence: 'high'
    }
  }

  if (volumeAssessment === llmAssessment) {
    return {
      finalAssessment: volumeAssessment,
      validationNote: 'Volume and LLM assessments agree',
      confidence: 'high'
    }
  }

  // Disagreement - prioritize volume-based assessment
  return {
    finalAssessment: volumeAssessment,
    validationNote: `INCONSISTENCY: Volume says ${volumeAssessment}, LLM says ${llmAssessment}. Using volume-based assessment (more reliable). ${volumeReasoning}`,
    confidence: 'medium'
  }
}

/**
 * Validate BT-RADS score assignment logic
 */
export function validateBTRADSScore(
  score: string,
  algorithmPath: string,
  imagingAssessment: string
): ValidationResult {
  const validation: ValidationResult = {
    isValid: true,
    issues: [],
    corrections: {},
    warnings: []
  }

  // Check score format
  const validScores = ['0', '1a', '1b', '2', '3a', '3b', '3c', '4']
  if (!validScores.includes(score)) {
    validation.issues.push(`Invalid BT-RADS score: ${score}`)
    validation.isValid = false
  }

  // Validate score matches algorithm path
  const pathValidation: Record<string, string[]> = {
    '0': ['NO_PRIOR'],
    '1a': ['TRUE_IMPROVEMENT', 'NO_MED_EFFECTS', 'SUSTAINED_AVASTIN'],
    '1b': ['AVASTIN', 'STEROID_EFFECT', 'CONSERVATIVE'],
    '2': ['UNCHANGED'],
    '3a': ['WITHIN_90_DAYS'],
    '3b': ['INDETERMINATE'],
    '3c': ['FAVOR_TUMOR', 'CONSERVATIVE'],
    '4': ['HIGHLY_SUSPICIOUS', 'PROGRESSIVE']
  }

  const expectedPatterns = pathValidation[score]
  if (expectedPatterns) {
    const hasValidPattern = expectedPatterns.some(pattern => 
      algorithmPath.includes(pattern)
    )
    
    if (!hasValidPattern) {
      validation.warnings.push(
        `BT-RADS ${score} assigned but algorithm path doesn't match expected patterns: ${algorithmPath}`
      )
    }
  }

  // Validate imaging assessment consistency
  if (score === '2' && imagingAssessment !== 'unchanged') {
    validation.issues.push('BT-2 assigned but imaging not unchanged')
    validation.isValid = false
  }

  if ((score === '1a' || score === '1b') && imagingAssessment !== 'improved') {
    validation.issues.push(`BT-${score} assigned but imaging not improved`)
    validation.isValid = false
  }

  if ((score === '3a' || score === '3b' || score === '3c' || score === '4') && 
      imagingAssessment !== 'worse') {
    validation.issues.push(`BT-${score} assigned but imaging not worse`)
    validation.isValid = false
  }

  return validation
}

/**
 * Calculate confidence level for the overall result
 */
export function calculateOverallConfidence(
  medicationConfidence: number,
  radiationConfidence: number,
  volumeDataAvailable: boolean,
  missingInfoCount: number
): {
  level: 'high' | 'medium' | 'low'
  score: number
  factors: string[]
} {
  const factors: string[] = []
  let score = 100

  // Medication extraction confidence
  if (medicationConfidence < 50) {
    score -= 20
    factors.push('Low medication extraction confidence')
  } else if (medicationConfidence < 80) {
    score -= 10
    factors.push('Medium medication extraction confidence')
  }

  // Radiation date confidence
  if (radiationConfidence < 50) {
    score -= 20
    factors.push('Low radiation date confidence')
  } else if (radiationConfidence < 80) {
    score -= 10
    factors.push('Medium radiation date confidence')
  }

  // Volume data availability
  if (!volumeDataAvailable) {
    score -= 15
    factors.push('No quantitative volume data')
  }

  // Missing information
  if (missingInfoCount > 0) {
    score -= missingInfoCount * 5
    factors.push(`${missingInfoCount} missing information items`)
  }

  // Determine level
  const level = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low'

  return { level, score, factors }
}