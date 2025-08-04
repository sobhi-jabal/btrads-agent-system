// Dedicated handler for LLM extraction results
import type { EvidenceItem } from '@/components/evidence/EvidenceHighlighter'

export interface LLMExtractionResult {
  steroidStatus: string
  avastinStatus: string
  onAvastin: boolean
  onSteroids: boolean
  medicationPath: string
  evidence: EvidenceItem[]
  reasoning: string
}

export interface LLMRadiationResult {
  radiationDate: string
  hasRadiation: boolean
  evidence: EvidenceItem[]
  reasoning: string
}

/**
 * Find the position of a sentence within the clinical note
 */
const findSentencePosition = (sentence: string, clinicalNote: string): { start: number; end: number } => {
  if (!sentence || !clinicalNote) {
    return { start: 0, end: 0 }
  }
  
  // First try exact match
  let startIndex = clinicalNote.indexOf(sentence)
  
  // If not found, try case-insensitive match
  if (startIndex === -1) {
    const lowerNote = clinicalNote.toLowerCase()
    const lowerSentence = sentence.toLowerCase()
    startIndex = lowerNote.indexOf(lowerSentence)
    
    // If still not found, try trimmed match
    if (startIndex === -1) {
      const trimmedSentence = sentence.trim()
      startIndex = clinicalNote.indexOf(trimmedSentence)
      
      if (startIndex === -1) {
        // Try normalized whitespace match
        const normalizedNote = clinicalNote.replace(/\s+/g, ' ')
        const normalizedSentence = sentence.replace(/\s+/g, ' ').trim()
        const normalizedStart = normalizedNote.indexOf(normalizedSentence)
        
        if (normalizedStart !== -1) {
          // Map back to original position (approximate)
          let originalPos = 0
          let normalizedPos = 0
          
          while (normalizedPos < normalizedStart && originalPos < clinicalNote.length) {
            if (clinicalNote[originalPos].match(/\s/)) {
              // Skip whitespace in original
              while (originalPos < clinicalNote.length && clinicalNote[originalPos].match(/\s/)) {
                originalPos++
              }
              normalizedPos++ // Single space in normalized
            } else {
              originalPos++
              normalizedPos++
            }
          }
          startIndex = originalPos
        }
      }
    }
  }
  
  // Calculate end index
  const endIndex = startIndex !== -1 ? startIndex + sentence.length : 0
  
  return {
    start: Math.max(0, startIndex),
    end: Math.max(0, endIndex)
  }
}

/**
 * Transform LLM evidence sentences into EvidenceItem format
 */
export const transformLLMEvidence = (llmEvidence: any[], clinicalNote?: string): EvidenceItem[] => {
  return llmEvidence
    .filter(item => item.llm_extracted === true) // Only use LLM-extracted evidence
    .map((item, index) => {
      // Use backend-provided positions if available, otherwise try to find them
      let startIndex = item.start_pos ?? 0
      let endIndex = item.end_pos ?? 0
      
      // Only try to find position if backend didn't provide it or didn't find it
      if ((!item.position_found || (startIndex === 0 && endIndex === 0)) && clinicalNote) {
        const position = findSentencePosition(item.text || '', clinicalNote)
        startIndex = position.start
        endIndex = position.end
      }
      
      return {
        id: `llm-evidence-${index}-${item.type}`,
        sourceText: item.text || '',
        matchedPattern: 'LLM extraction',
        confidence: 'high' as const,
        startIndex: startIndex,
        endIndex: endIndex,
        category: item.category || item.type || 'general',
        reasoning: `Extracted by LLM with ${(item.confidence * 100).toFixed(0)}% confidence`,
        relevanceScore: item.relevance_score || 1.0,
        patternType: 'llm_extraction',
        fullContext: item.text // The full sentence is the context
      }
    })
}

/**
 * Handle LLM medication extraction results
 */
export const handleLLMMedications = (llmMeds: any, clinicalNote?: string): LLMExtractionResult => {
  const steroidStatus = llmMeds.data?.steroid_status || 'unknown'
  const avastinStatus = llmMeds.data?.avastin_status || 'unknown'
  
  // Convert status to boolean flags
  const onAvastin = avastinStatus !== 'none' && avastinStatus !== 'unknown'
  const onSteroids = steroidStatus !== 'none' && steroidStatus !== 'unknown'
  
  // Determine medication path
  let medicationPath = 'neither'
  if (onAvastin) medicationPath = 'avastin'
  else if (onSteroids) medicationPath = 'steroids'
  
  // Transform evidence with clinical note for position finding
  const evidence = transformLLMEvidence(llmMeds.evidence || [], clinicalNote)
  
  // Build reasoning based on LLM extraction
  let reasoning = ''
  if (onAvastin && onSteroids) {
    reasoning = `LLM identified both Avastin (${avastinStatus}) and steroids (${steroidStatus}) from the clinical note. `
    reasoning += `Evidence: ${evidence.map(e => `"${e.sourceText}"`).join('; ')}`
  } else if (onAvastin) {
    reasoning = `LLM identified Avastin therapy (${avastinStatus}) from the clinical note. `
    const avastinEvidence = evidence.find(e => e.category === 'medication' && e.sourceText.toLowerCase().includes('avastin'))
    if (avastinEvidence) {
      reasoning += `Evidence: "${avastinEvidence.sourceText}"`
    }
  } else if (onSteroids) {
    reasoning = `LLM identified steroid therapy (${steroidStatus}) from the clinical note. `
    const steroidEvidence = evidence.find(e => e.category === 'medication' && 
      (e.sourceText.toLowerCase().includes('dexamethasone') || 
       e.sourceText.toLowerCase().includes('steroid') ||
       e.sourceText.toLowerCase().includes('decadron')))
    if (steroidEvidence) {
      reasoning += `Evidence: "${steroidEvidence.sourceText}"`
    }
  } else {
    reasoning = 'LLM did not identify any relevant medications in the clinical note.'
  }
  
  return {
    steroidStatus,
    avastinStatus,
    onAvastin,
    onSteroids,
    medicationPath,
    evidence,
    reasoning
  }
}

/**
 * Handle LLM radiation date extraction results
 */
export const handleLLMRadiation = (llmRad: any, clinicalNote?: string): LLMRadiationResult => {
  const radiationDate = llmRad.data?.radiation_date || 'unknown'
  const hasRadiation = radiationDate !== 'unknown' && radiationDate !== 'no_radiation'
  
  // Transform evidence with clinical note for position finding
  const evidence = transformLLMEvidence(llmRad.evidence || [], clinicalNote)
  
  // Build reasoning
  let reasoning = ''
  if (hasRadiation) {
    reasoning = `LLM extracted radiation completion date: ${radiationDate}. `
    if (evidence.length > 0) {
      reasoning += `Evidence: "${evidence[0].sourceText}"`
    }
  } else if (radiationDate === 'no_radiation') {
    reasoning = 'LLM determined patient has not received radiation therapy.'
  } else {
    reasoning = 'LLM could not determine radiation date from the clinical note.'
  }
  
  return {
    radiationDate,
    hasRadiation,
    evidence,
    reasoning
  }
}