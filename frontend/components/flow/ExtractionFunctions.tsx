// Extraction helper functions for BT-RADS Decision Flow
import { api } from '@/lib/api/client'

export type ExtractionMode = 'nlp' | 'llm' | 'both'

export interface ExtractionResult {
  nlp?: {
    medications?: { steroidStatus: string; avastinStatus: string; evidence: any[] }
    radiationDate?: { date: string; evidence: any[] }
  }
  llm?: {
    medications?: { data: any; evidence: any[]; confidence: number; processing_time: number }
    radiationDate?: { data: any; evidence: any[]; confidence: number; processing_time: number }
  }
}

export const extractMedicationsNLP = (text: string) => {
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
  
  // Enhanced status detection
  let steroidStatus = 'none'
  let avastinStatus = 'none'
  
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
  
  return {
    steroidStatus,
    avastinStatus,
    evidence: evidence.slice(0, 5)
  }
}

export const extractRadiationDateNLP = (text: string) => {
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
  
  let radiationDate = 'unknown'
  const evidence: any[] = []
  
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
        break
      }
    }
  }
  
  return { date: radiationDate, evidence }
}

export const extractDataPoints = async (text: string, mode: ExtractionMode) => {
  const results: ExtractionResult = {}
  
  if (mode === 'nlp' || mode === 'both') {
    results.nlp = {
      medications: extractMedicationsNLP(text),
      radiationDate: extractRadiationDateNLP(text)
    }
  }
  
  if (mode === 'llm' || mode === 'both') {
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
      
      results.llm = {
        medications: medicationsResponse,
        radiationDate: radiationResponse
      }
    } catch (error) {
      console.error('LLM extraction error:', error)
      // Return error state
      results.llm = {
        medications: {
          data: { steroid_status: 'unknown', avastin_status: 'unknown' },
          evidence: [],
          confidence: 0,
          processing_time: 0,
          error: error instanceof Error ? error.message : 'LLM extraction failed'
        },
        radiationDate: {
          data: { radiation_date: 'unknown' },
          evidence: [],
          confidence: 0,
          processing_time: 0,
          error: error instanceof Error ? error.message : 'LLM extraction failed'
        }
      }
    }
  }
  
  return results
}