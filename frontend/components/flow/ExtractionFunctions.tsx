// Extraction helper functions for BT-RADS Decision Flow
import { api } from '@/lib/api/client'
import type { ExtractionResult as MissingInfoExtractionResult } from '@/types/missing-info'
import type { EvidenceItem } from '@/components/evidence/EvidenceHighlighter'

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

// Transform backend evidence to EvidenceHighlighter format
export const transformEvidence = (evidence: any[], clinicalNote?: string): EvidenceItem[] => {
  return evidence.map((item, index) => {
    // Extract full context if available
    let fullContext = ''
    if (clinicalNote && item.context_start !== undefined && item.context_end !== undefined) {
      fullContext = clinicalNote.substring(item.context_start, item.context_end).trim()
    } else if (item.text) {
      fullContext = item.text
    }
    
    return {
      id: `evidence-${index}-${item.start_pos || index}`,
      sourceText: item.matched_text || item.mention || item.text || '',
      matchedPattern: item.pattern || 'unknown',
      confidence: item.confidence > 0.85 ? 'high' : item.confidence > 0.7 ? 'medium' : 'low',
      startIndex: item.start_pos || item.context_start || 0,
      endIndex: item.end_pos || item.context_end || 0,
      category: item.category || item.type || 'general',
      alternatives: [],
      reasoning: item.pattern_type ? `Pattern type: ${item.pattern_type}` : undefined,
      relevanceScore: item.relevance_score || item.relevance,
      patternType: item.pattern_type,
      fullContext: fullContext
    }
  })
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
          text: match[0],
          mention: match[0],
          start_pos: match.index,
          end_pos: match.index + match[0].length,
          context_start: start,
          context_end: end,
          relevance: 0.8,
          source: 'nlp_pattern',
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
          text: match[0],
          mention: match[0],
          start_pos: match.index,
          end_pos: match.index + match[0].length,
          context_start: start,
          context_end: end,
          relevance: 0.8,
          source: 'nlp_pattern',
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
    evidence: evidence.slice(0, 5) // Return full evidence objects, not just text
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
    /(\d{1,2}\/\d{1,2}\/\d{2,4}).*?radiation.*?complet/gi,
    /started\s+on\s+(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
    /last\s+dosed?\s+on\s+(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
    /(\d{1,2}\/\d{1,2}\/\d{2,4})\s*\(.*?(?:radiation|xrt|therapy)/gi
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
        text: match[0],
        date: radiationDate,
        start_pos: match.index!,
        end_pos: match.index! + match[0].length,
        context_start: start,
        context_end: end,
        relevance: 0.9,
        source: 'nlp_pattern',
        startDate: match[1],
        endDate: match[2],
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
          text: match[0],
          date: radiationDate,
          start_pos: match.index!,
          end_pos: match.index! + match[0].length,
          context_start: start,
          context_end: end,
          relevance: 0.85,
          source: 'nlp_pattern',
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
    evidence: evidence // Return full evidence objects
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

// LLM extraction using Ollama with phi4
export const extractDataPointsLLM = async (text: string, followupDate?: string) => {
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
        isMissing: false  // LLM extraction succeeded, even if values are "unknown"
      },
      radiationDate: {
        ...radiationResponse,
        isMissing: false  // LLM extraction succeeded, even if values are "unknown"
      }
    }
  } catch (error) {
    console.error('LLM extraction failed:', error)
    // Return error state with isMissing = true
    return {
      medications: {
        data: null,
        error: error.message || 'LLM extraction failed',
        confidence: 0,
        processing_time: 0,
        isMissing: true,  // Mark as missing when extraction actually fails
        evidence: []
      },
      radiationDate: {
        data: null,
        error: error.message || 'LLM extraction failed',
        confidence: 0,
        processing_time: 0,
        isMissing: true,  // Mark as missing when extraction actually fails
        evidence: []
      }
    }
  }
}

// Main orchestrator function - coordinates NLP and LLM extraction
export const extractDataPoints = async (text: string, mode: ExtractionMode, followupDate?: string): Promise<ExtractionResult> => {
  const results: ExtractionResult = {}
  
  console.log(`[Extraction] Starting extraction with mode: ${mode}`)
  
  try {
    // Extract based on mode - no fallbacks
    if (mode === 'nlp') {
      results.nlp = extractDataPointsNLP(text)
      console.log('[Extraction] NLP results:', results.nlp)
    } else if (mode === 'llm') {
      const llmResults = await extractDataPointsLLM(text, followupDate)
      results.llm = llmResults
      console.log('[Extraction] LLM results:', results.llm)
    } else if (mode === 'both') {
      // Run both independently
      results.nlp = extractDataPointsNLP(text)
      const llmResults = await extractDataPointsLLM(text, followupDate)
      results.llm = llmResults
      console.log('[Extraction] Both results:', { nlp: results.nlp, llm: results.llm })
    }
  } catch (error) {
    console.error('[Extraction] Error during extraction:', error)
    throw error // Re-throw to handle in parent
  }
  
  return results
}