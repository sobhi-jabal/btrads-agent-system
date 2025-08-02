// Types for handling missing information in BT-RADS decision flow

export type MissingInfoType = 
  | 'medication_status'
  | 'radiation_date'
  | 'volume_data'
  | 'prior_imaging'
  | 'clinical_assessment'

export type MissingInfoSeverity = 'critical' | 'important' | 'optional'

export interface FallbackOption {
  id: string
  label: string
  value: any
  description?: string
  isConservative?: boolean
  consequences?: string
}

export interface MissingInfoItem {
  id: string
  type: MissingInfoType
  field: string
  label: string
  description: string
  severity: MissingInfoSeverity
  requiredFor: string[]
  currentValue?: any
  confidence?: number
  extractionMethod?: 'nlp' | 'llm' | 'manual'
  fallbackOptions?: FallbackOption[]
  defaultFallback?: string
  validationRules?: {
    type?: 'date' | 'number' | 'text' | 'boolean'
    min?: number
    max?: number
    pattern?: string
    required?: boolean
  }
}

export interface UserProvidedData {
  itemId: string
  providedValue: any
  selectedFallback?: string
  confirmedMissing?: boolean
  notes?: string
  timestamp: Date
  provider?: string
}

export interface MissingInfoState {
  items: MissingInfoItem[]
  userProvidedData: Record<string, UserProvidedData>
  isResolving: boolean
  currentItemIndex: number
}

export interface ExtractionResult {
  value: any
  confidence: number
  isMissing: boolean
  source?: string
  evidence?: string[]
  alternativeValues?: any[]
}

export interface DataValidation {
  isValid: boolean
  errors?: string[]
  warnings?: string[]
  suggestions?: string[]
}

// Predefined fallback options for common scenarios
export const MEDICATION_FALLBACK_OPTIONS: FallbackOption[] = [
  {
    id: 'no_medications',
    label: 'No medications',
    value: { steroidStatus: 'none', avastinStatus: 'none' },
    description: 'Patient is not on Avastin or steroids',
    isConservative: false
  },
  {
    id: 'unknown_assume_none',
    label: 'Unknown - Assume none',
    value: { steroidStatus: 'unknown', avastinStatus: 'unknown' },
    description: 'Cannot determine medication status, proceed as if no medications',
    isConservative: true,
    consequences: 'May lead to BT-1a (true improvement) if improvement detected'
  },
  {
    id: 'unknown_assume_present',
    label: 'Unknown - Assume medications present',
    value: { steroidStatus: 'unknown', avastinStatus: 'unknown' },
    description: 'Cannot determine, but assume medication effects possible',
    isConservative: true,
    consequences: 'May lead to BT-1b (medication effect) if improvement detected'
  }
]

export const RADIATION_DATE_FALLBACK_OPTIONS: FallbackOption[] = [
  {
    id: 'within_90_days',
    label: 'Within 90 days',
    value: 'within_90_days',
    description: 'Radiation completed within the last 90 days',
    isConservative: true,
    consequences: 'May lead to BT-3a (treatment effect) if worsening detected'
  },
  {
    id: 'more_than_90_days',
    label: 'More than 90 days ago',
    value: 'more_than_90_days',
    description: 'Radiation completed more than 90 days ago',
    isConservative: false
  },
  {
    id: 'no_radiation',
    label: 'No prior radiation',
    value: 'no_radiation',
    description: 'Patient has not received radiation therapy',
    isConservative: false
  },
  {
    id: 'unknown_assume_recent',
    label: 'Unknown - Assume recent',
    value: 'unknown',
    description: 'Cannot determine, assume possible recent radiation',
    isConservative: true,
    consequences: 'May lead to BT-3a (treatment effect) if worsening detected'
  }
]

export const VOLUME_FALLBACK_OPTIONS: FallbackOption[] = [
  {
    id: 'use_qualitative',
    label: 'Use qualitative assessment',
    value: 'qualitative',
    description: 'Proceed with radiologist\'s qualitative assessment instead of volumes',
    isConservative: true
  },
  {
    id: 'estimate_from_report',
    label: 'Estimate from report',
    value: 'estimate',
    description: 'Use size descriptions from report to estimate volumes',
    isConservative: true
  },
  {
    id: 'skip_volume_based',
    label: 'Skip volume-based assessment',
    value: 'skip',
    description: 'Proceed without volume data (may limit accuracy)',
    isConservative: true,
    consequences: 'Assessment will rely on other clinical factors'
  }
]