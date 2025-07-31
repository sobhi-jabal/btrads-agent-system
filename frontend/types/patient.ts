export interface PatientData {
  patient_id: string
  clinical_note: string
  baseline_date: string
  followup_date: string
  radiation_date?: string | null
  baseline_flair_volume?: number | null
  followup_flair_volume?: number | null
  flair_change_percentage?: number | null
  baseline_enhancement_volume?: number | null
  followup_enhancement_volume?: number | null
  enhancement_change_percentage?: number | null
  ground_truth_btrads?: string | null
}

export interface Patient {
  id: string
  created_at: string
  updated_at: string
  data: PatientData
  processing_status: 'pending' | 'processing' | 'completed' | 'error'
  current_node?: string | null
  completed: boolean
}