// Extraction helper functions for BT-RADS Decision Flow
import { api } from '@/lib/api/client'
import type { ExtractionResult as MissingInfoExtractionResult } from '@/types/missing-info'

export type ExtractionMode = 'nlp' | 'llm' | 'both'

export interface ExtractionResult {
  nlp?: {
    medications?: { 
      steroidStatus: string
      avastinStatus: string
      evidence: any[]
      confidence?: number
      isMissing?: boolean
    }
    radiationDate?: { 
      date: string
      evidence: any[]
      confidence?: number
      isMissing?: boolean
    }
  }
  llm?: {
    medications?: { 
      data: any
      evidence: any[]
      confidence: number
      processing_time: number
      isMissing?: boolean
      error?: string
    }
    radiationDate?: { 
      data: any
      evidence: any[]
      confidence: number
      processing_time: number
      isMissing?: boolean
      error?: string
    }
  }
}

export const extractMedicationsNLP = (text: string): MissingInfoExtractionResult => {
  const clinicalNote = text.toLowerCase()
  
  // Avastin patterns
  const avastinPatterns = [
    /avastin/gi, /bevacizumab/gi, /bev\b/gi, /anti-angiogenic/gi,
    /vegf\s*inhibitor/gi, /anti-vegf/gi
  ]
  const hasAvastin = avastinPatterns.some(p => p.test(clinicalNote))
  
  // Steroid patterns
  const steroidPatterns = [
    /steroid/gi, /dexamethasone/gi, /decadron/gi, /predniso/gi,
    /methylprednisolone/gi, /solu-medrol/gi
  ]
  const hasSteroid = steroidPatterns.some(p => p.test(clinicalNote))
  
  // Check for negative patterns that reduce confidence
  const negativePatterns = [
    /no\s+(steroid|avastin|medication)/gi,
    /not\s+on\s+(steroid|avastin)/gi,
    /discontinued\s+(steroid|avastin)/gi,
    /off\s+(steroid|avastin)/gi
  ]
  const hasNegativePattern = negativePatterns.some(p => p.test(clinicalNote))
  
  // Enhanced status detection
  let steroidStatus = 'none'
  let avastinStatus = 'none'
  let confidence = 0
  
  if (hasSteroid) {
    if (/increas\w*\s*(?:dose|dosage)?\s*(?:of\s*)?(?:steroid|dexamethasone|decadron)/gi.test(clinicalNote) ||
        /(?:steroid|dexamethasone|decadron)\s*(?:dose|dosage)?\s*increas/gi.test(clinicalNote)) {
      steroidStatus = 'increasing'
    } else if (/start\w*\s*(?:on\s*)?(?:steroid|dexamethasone|decadron)/gi.test(clinicalNote)) {
      steroidStatus = 'started'
    } else if (/taper\w*\s*(?:steroid|dexamethasone|decadron)/gi.test(clinicalNote) ||
               /decreas\w*\s*(?:dose|dosage)?\s*(?:of\s*)?(?:steroid|dexamethasone|decadron)/gi.test(clinicalNote)) {
      steroidStatus = 'decreasing'
    } else {
      steroidStatus = 'stable'
    }
  }
  
  if (hasAvastin) {
    if (/first\s*(?:dose|infusion|treatment)?\s*(?:of\s*)?(?:avastin|bevacizumab)/gi.test(clinicalNote) ||
        /(?:avastin|bevacizumab)\s*(?:started|initiated)/gi.test(clinicalNote)) {
      avastinStatus = 'first_treatment'
    } else if (/start\w*\s*(?:on\s*)?(?:avastin|bevacizumab)/gi.test(clinicalNote)) {
      avastinStatus = 'started'
    } else {
      avastinStatus = 'ongoing'
    }
  }
  
  // Extract evidence
  const evidence: any[] = []
  const originalText = text
  
  // Find Avastin evidence
  avastinPatterns.forEach(pattern => {
    const matches = originalText.matchAll(pattern)
    for (const match of matches) {
      if (match.index !== undefined) {
        const start = Math.max(0, match.index - 50)
        const end = Math.min(originalText.length, match.index + match[0].length + 50)
        evidence.push({
          type: 'avastin',
          text: originalText.slice(start, end),
          pattern: pattern.source,
          medication: 'avastin'
        })
      }
    }
  })
  
  // Find steroid evidence
  steroidPatterns.forEach(pattern => {
    const matches = originalText.matchAll(pattern)
    for (const match of matches) {
      if (match.index !== undefined) {
        const start = Math.max(0, match.index - 50)
        const end = Math.min(originalText.length, match.index + match[0].length + 50)
        evidence.push({
          type: 'steroid',
          text: originalText.slice(start, end),
          pattern: pattern.source,
          medication: 'steroid'
        })
      }
    }
  })
  
  // Calculate confidence
  if (!hasAvastin && !hasSteroid) {
    // No medication mentions found
    confidence = hasNegativePattern ? 85 : 30 // Higher confidence if explicit negative
  } else {
    // Medications found
    const evidenceCount = evidence.length
    if (evidenceCount >= 3) confidence = 95
    else if (evidenceCount >= 2) confidence = 85
    else if (evidenceCount >= 1) confidence = 70
    else confidence = 50
    
    // Reduce confidence if negative patterns found
    if (hasNegativePattern) confidence -= 20
  }
  
  // Determine if missing
  const isMissing = confidence < 50 && !hasNegativePattern
  
  return {
    value: {
      steroidStatus,
      avastinStatus,
      evidence: evidence.slice(0, 5)
    },
    confidence,
    isMissing,
    source: 'nlp_pattern_matching',
    evidence: evidence.map(e => e.text)
  }
}

export const extractRadiationDateNLP = (text: string): MissingInfoExtractionResult => {
  // Date range patterns (capture both start and end)
  const dateRangePatterns = [
    /radiation.*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[-–]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
    /(?:xrt|radiotherapy).*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[-–]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
    /(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[-–]\s*(\d{1,2}\/\d{1,2}\/\d{2,4}).*?(?:radiation|xrt|radiotherapy)/gi
  ]
  
  // Single date patterns
  const singleDatePatterns = [
    /radiation.*?complet\w*.*?(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
    /(?:xrt|rt|radiotherapy).*?(?:complet\w*|finish\w*).*?(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
    /(\d{1,2}\/\d{1,2}\/\d{2,4}).*?radiation.*?complet/gi
  ]
  
  // Check for radiation mentions without dates
  const radiationMentions = [
    /radiation/gi, /xrt/gi, /radiotherapy/gi, /rt\b/gi
  ]
  const hasRadiationMention = radiationMentions.some(p => p.test(text))
  
  // Check for no radiation patterns
  const noRadiationPatterns = [
    /no\s+(?:prior\s+)?radiation/gi,
    /never\s+(?:had\s+)?radiation/gi,
    /radiation\s+naive/gi
  ]
  const hasNoRadiation = noRadiationPatterns.some(p => p.test(text))
  
  let radiationDate = 'unknown'
  const evidence: any[] = []
  let confidence = 0
  
  // First try date ranges (use end date)
  for (const pattern of dateRangePatterns) {
    const match = text.match(pattern)
    if (match && match[2]) {
      radiationDate = match[2] // Use end date
      const start = Math.max(0, match.index! - 50)
      const end = Math.min(text.length, match.index! + match[0].length + 50)
      evidence.push({
        type: 'radiation_date_range',
        text: text.slice(start, end),
        startDate: match[1],
        endDate: match[2],
        date: radiationDate,
        pattern: pattern.source
      })
      confidence = 95 // High confidence with date range
      break
    }
  }
  
  // If no range found, try single dates
  if (radiationDate === 'unknown') {
    for (const pattern of singleDatePatterns) {
      const match = text.match(pattern)
      if (match && match[1]) {
        radiationDate = match[1]
        const start = Math.max(0, match.index! - 50)
        const end = Math.min(text.length, match.index! + match[0].length + 50)
        evidence.push({
          type: 'radiation_date',
          text: text.slice(start, end),
          date: radiationDate,
          pattern: pattern.source
        })
        confidence = 85 // Good confidence with single date
        break
      }
    }
  }
  
  // Calculate confidence and missing status
  if (radiationDate === 'unknown') {
    if (hasNoRadiation) {
      radiationDate = 'no_radiation'
      confidence = 90 // High confidence in no radiation
    } else if (hasRadiationMention) {
      confidence = 20 // Low confidence - radiation mentioned but no date
    } else {
      confidence = 10 // Very low confidence - no radiation info at all
    }
  }
  
  const isMissing = radiationDate === 'unknown' && hasRadiationMention
  
  return {
    value: { date: radiationDate, evidence },
    confidence,
    isMissing,
    source: 'nlp_pattern_matching',
    evidence: evidence.map(e => e.text)
  }
}

// Separate NLP extraction - always works, no external dependencies
export const extractDataPointsNLP = (text: string) => {
  const medsResult = extractMedicationsNLP(text)
  const radResult = extractRadiationDateNLP(text)
  
  return {
    medications: {
      steroidStatus: medsResult.value.steroidStatus,
      avastinStatus: medsResult.value.avastinStatus,
      evidence: medsResult.value.evidence,
      confidence: medsResult.confidence,
      isMissing: medsResult.isMissing
    },
    radiationDate: {
      date: radResult.value.date,
      evidence: radResult.value.evidence,
      confidence: radResult.confidence,
      isMissing: radResult.isMissing
    }
  }
}

// Separate LLM extraction - optional, can fail gracefully
export const extractDataPointsLLM = async (text: string) => {
  try {
    const [medicationsResponse, radiationResponse] = await Promise.all([
      api.llm.extract({
        clinical_note: text,
        extraction_type: 'medications',
        model: 'phi4:14b'
      }),
      api.llm.extract({
        clinical_note: text,
        extraction_type: 'radiation_date',
        model: 'phi4:14b'
      })
    ])
    
    // Check for low confidence or missing data in LLM results
    const medConfidence = medicationsResponse.confidence || 0
    const radConfidence = radiationResponse.confidence || 0
    
    return {
      medications: {
        ...medicationsResponse,
        isMissing: medConfidence < 50 || 
          (medicationsResponse.data?.steroid_status === 'unknown' && 
           medicationsResponse.data?.avastin_status === 'unknown')
      },
      radiationDate: {
        ...radiationResponse,
        isMissing: radConfidence < 50 || 
          radiationResponse.data?.radiation_date === 'unknown'
      }
    }
  } catch (error) {
    console.error('LLM extraction error:', error)
    // Return null on error - let the caller handle it
    return null
  }
}

// Main orchestrator function - coordinates NLP and LLM extraction
export const extractDataPoints = async (text: string, mode: ExtractionMode): Promise<ExtractionResult> => {
  const results: ExtractionResult = {}
  
  // Always run NLP extraction first (never fails)
  if (mode === 'nlp' || mode === 'both') {
    results.nlp = extractDataPointsNLP(text)
  }
  
  // Then try LLM if requested
  if (mode === 'llm' || mode === 'both') {
    const llmResults = await extractDataPointsLLM(text)
    if (llmResults) {
      results.llm = llmResults
    } else {
      // LLM failed but we can continue with NLP results
      console.log('LLM extraction failed, continuing with NLP results only')
    }
  }
  
  return results
}