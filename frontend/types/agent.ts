export interface HighlightedSource {
  text: string
  start_char: number
  end_char: number
  confidence: number
}

export interface MissingInfo {
  field: string
  reason: string
  clinical_impact: string
  suggested_fallback?: string
}

export interface AgentResult {
  agent_id: string
  node_id: string
  patient_id: string
  timestamp: string
  extracted_value: any
  confidence: number
  reasoning: string
  source_highlights: HighlightedSource[]
  validation_status: 'pending' | 'approved' | 'modified' | 'flagged'
  validated_value?: any
  validator_notes?: string
  validated_by?: string
  validated_at?: string
  missing_info: MissingInfo[]
  processing_time_ms: number
  llm_model: string
  validation_id?: string
  validation_options?: Array<{
    value: any
    label: string
    description?: string
  }>
}