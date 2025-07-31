'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { 
  ChevronRight, 
  ChevronDown, 
  ChevronUp,
  CheckCircle, 
  Clock, 
  AlertCircle,
  ArrowDown,
  ArrowRight,
  Database,
  FileText,
  Stethoscope,
  Activity,
  Zap,
  Brain,
  Loader2
} from "lucide-react"
import { getBTRADSNodes, getBTRADSEdges } from '@/lib/flowchart/flowchart-config'
import { ConnectionLine } from './ConnectionLine'
import { api } from '@/lib/api/client'
import { EvidenceHighlighter, type EvidenceItem } from '@/components/evidence/EvidenceHighlighter'
import { CalculationBreakdown, type CalculationStep } from '@/components/evidence/CalculationBreakdown'
import { ConfidenceIndicator, type ConfidenceData } from '@/components/evidence/ConfidenceIndicator'
import { DecisionAuditTrail, type DecisionPoint, type DecisionCriteria, type AlternativePath } from '@/components/evidence/DecisionAuditTrail'
import { ManualVerificationPanel, type VerificationItem } from '@/components/evidence/ManualVerificationPanel'
import { BTRADSFinalScore } from './BTRADSFinalScore'
import { 
  extractDataPoints, 
  extractMedicationsNLP, 
  extractRadiationDateNLP,
  type ExtractionMode,
  type ExtractionResult 
} from './ExtractionFunctions'
import { ExtractionComparison } from './BTRADSComparisonView'

// BT-RADS Measurable Disease Threshold: 1 mL = 1×1×1 cm
const MEASURABLE_DISEASE_THRESHOLD = 1.0

interface BTRADSDecisionFlowProps {
  patientId: string
  onProcessingComplete?: (result: any) => void
  autoStart?: boolean
  onProcessNext?: () => void
  onProcessPrevious?: () => void
  hasNextPatient?: boolean
  hasPreviousPatient?: boolean
  remainingCount?: number
  completedCount?: number
  extractionMode?: ExtractionMode
}

interface ProcessingStep {
  nodeId: string
  label: string
  type: 'data-extraction' | 'decision' | 'outcome'
  status: 'pending' | 'processing' | 'completed' | 'error'
  data?: any
  reasoning?: string
  nextNode?: string
  btradsScore?: string
  // Enhanced transparency fields
  evidence?: EvidenceItem[]
  calculations?: CalculationStep[]
  confidence?: ConfidenceData
  decisionPoint?: DecisionPoint
  verificationItems?: VerificationItem[]
}

export function BTRADSDecisionFlow({ 
  patientId, 
  onProcessingComplete, 
  autoStart = false,
  onProcessNext,
  onProcessPrevious,
  hasNextPatient,
  hasPreviousPatient,
  remainingCount,
  completedCount,
  extractionMode = 'both'
}: BTRADSDecisionFlowProps) {
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([])
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [patientData, setPatientData] = useState<any>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  const [transparencyLevel, setTransparencyLevel] = useState<'simple' | 'detailed' | 'expert' | 'audit'>('detailed')
  const [decisionTrail, setDecisionTrail] = useState<DecisionPoint[]>([])
  const [autoAdvance, setAutoAdvance] = useState(false)
  // extractionMode is now passed as a prop
  const [extractionResults, setExtractionResults] = useState<ExtractionResult>({})

  // Initialize with flowchart nodes
  useEffect(() => {
    const nodes = getBTRADSNodes()
    const initialSteps: ProcessingStep[] = nodes.map(node => ({
      nodeId: node.id,
      label: node.data.label,
      type: node.data.type,
      status: 'pending',
      btradsScore: node.data.btradsScore
    }))
    
    setProcessingSteps(initialSteps)
  }, [])

  // Auto-expand completed steps (main reasoning)
  useEffect(() => {
    processingSteps.forEach((step, index) => {
      if (step.status === 'completed' && !expandedSteps.has(index)) {
        setExpandedSteps(prev => new Set([...prev, index]))
      }
    })
  }, [processingSteps])

  // Load patient data
  useEffect(() => {
    const loadPatientData = async () => {
      try {
        const patient = await api.patients.getById(patientId)
        setPatientData(patient)
        
        // Auto-start processing if enabled
        if (autoStart && !isProcessing) {
          // Small delay to let UI render first
          setTimeout(() => {
            startProcessing()
          }, 500)
        }
      } catch (error) {
        console.error('Error loading patient data:', error)
      }
    }

    if (patientId) {
      loadPatientData()
    }
  }, [patientId])

  const startProcessing = async () => {
    setIsProcessing(true)
    setCurrentStep(0)
    
    try {
      // Extract data points first if we have clinical note
      if (patientData?.data?.clinical_note) {
        const results = await extractDataPoints(patientData.data.clinical_note, extractionMode)
        setExtractionResults(results)
      }
      
      // Start the actual processing
      await api.patients.startProcessing(patientId, false)
      
      // Simulate step-by-step processing for demonstration
      await simulateProcessingSteps()
      
    } catch (error) {
      console.error('Error during processing:', error)
      setProcessingSteps(prev => prev.map((step, index) => 
        index === currentStep ? { ...step, status: 'error' } : step
      ))
    } finally {
      setIsProcessing(false)
    }
  }

  const simulateProcessingSteps = async () => {
    let currentNodeId = 'start'
    const processedNodes = new Set<string>()
    
    while (currentNodeId && !processedNodes.has(currentNodeId)) {
      processedNodes.add(currentNodeId)
      
      // Find the step index for the current node
      const stepIndex = processingSteps.findIndex(step => step.nodeId === currentNodeId)
      if (stepIndex === -1) break
      
      setCurrentStep(stepIndex)
      
      // Update step status to processing
      setProcessingSteps(prev => prev.map((step, index) => 
        index === stepIndex ? { ...step, status: 'processing' } : step
      ))
      
      // Simulate processing delay with variable timing based on step type
      const processingTime = processingSteps[stepIndex].type === 'data-extraction' ? 1500 : 
                           processingSteps[stepIndex].type === 'decision' ? 1000 : 500
      await new Promise(resolve => setTimeout(resolve, processingTime))
      
      // Update step with results
      const processedStep = await processStep(processingSteps[stepIndex], patientData)
      
      setProcessingSteps(prev => prev.map((step, index) => 
        index === stepIndex ? processedStep : step
      ))
      
      // Move to next node based on decision
      currentNodeId = processedStep.nextNode || ''
      
      // If this is an outcome node, stop processing
      if (processedStep.type === 'outcome' && processedStep.status === 'completed') {
        // Expand the final outcome step
        setExpandedSteps(prev => new Set([...prev, stepIndex]))
        
        // Call onProcessingComplete callback with result
        if (onProcessingComplete) {
          onProcessingComplete({
            btradsScore: processedStep.btradsScore,
            reasoning: processedStep.reasoning,
            steps: processingSteps,
            patientId
          })
        }
        
        break
      }
    }
  }

  // Helper function to create evidence items from pattern matches
  const createEvidence = (
    text: string, 
    patterns: RegExp[], 
    category: string,
    patternNames?: string[]
  ): EvidenceItem[] => {
    const evidence: EvidenceItem[] = []
    let evidenceId = 0

    patterns.forEach((pattern, index) => {
      const matches = Array.from(text.matchAll(pattern))
      matches.forEach(match => {
        if (match.index !== undefined) {
          evidence.push({
            id: `${category}-${evidenceId++}`,
            sourceText: match[0],
            matchedPattern: patternNames?.[index] || pattern.source,
            confidence: match[0].length > 3 ? 'high' : 'medium',
            startIndex: match.index,
            endIndex: match.index + match[0].length,
            category,
            reasoning: `Matched pattern: ${patternNames?.[index] || pattern.source}`
          })
        }
      })
    })

    return evidence
  }

  // Helper function to create calculation steps
  const createCalculation = (
    id: string,
    label: string,
    formula: string,
    inputs: Record<string, number | string>,
    result: number | string,
    unit?: string,
    explanation?: string,
    threshold?: { value: number; operator: string }
  ): CalculationStep => {
    return {
      id,
      label,
      formula,
      inputs,
      result,
      unit,
      explanation,
      isThreshold: threshold !== undefined,
      thresholdValue: threshold?.value,
      comparisonOperator: threshold?.operator as any
    }
  }

  // Helper function to create confidence data
  const createConfidenceData = (
    evidenceQuality: number,
    dataCompleteness: number,
    patternMatches: number,
    clinicalCoherence: number,
    reasoning: string,
    uncertainties?: string[],
    alternatives?: string[]
  ): ConfidenceData => {
    const overall = Math.round((evidenceQuality + dataCompleteness + patternMatches + clinicalCoherence) / 4)
    
    let level: ConfidenceData['level']
    if (overall >= 90) level = 'very-high'
    else if (overall >= 75) level = 'high'
    else if (overall >= 60) level = 'medium'
    else if (overall >= 40) level = 'low'
    else level = 'very-low'

    return {
      overall,
      factors: {
        evidenceQuality,
        dataCompleteness,
        patternMatches,
        clinicalCoherence
      },
      level,
      reasoning,
      uncertainties,
      alternatives
    }
  }

  const processStep = async (step: ProcessingStep, patient: any): Promise<ProcessingStep> => {
    // Enhanced processing logic that follows BT-RADS flowchart exactly
    switch (step.nodeId) {
      case 'start':
        return {
          ...step,
          status: 'completed',
          data: {
            patientId: patient?.data?.patient_id,
            clinicalNote: patient?.data?.clinical_note?.substring(0, 150) + '...',
            baselineDate: patient?.data?.baseline_date,
            followupDate: patient?.data?.followup_date
          },
          reasoning: 'Successfully loaded patient clinical data, imaging information, and volume measurements.',
          nextNode: 'node_1_suitable_prior'
        }
      
      case 'node_1_suitable_prior':
        const hasPrior = patient?.data?.baseline_date && patient?.data?.followup_date
        return {
          ...step,
          status: 'completed',
          data: {
            hasPrior: hasPrior ? 'Yes' : 'No',
            baselineDate: patient?.data?.baseline_date,
            followupDate: patient?.data?.followup_date,
            daysBetween: hasPrior ? Math.floor((new Date(patient.data.followup_date).getTime() - new Date(patient.data.baseline_date).getTime()) / (1000 * 60 * 60 * 24)) : 0
          },
          reasoning: hasPrior 
            ? `Patient has suitable prior imaging: baseline (${patient.data.baseline_date}) and follow-up (${patient.data.followup_date})`
            : 'No suitable prior imaging available - requires baseline scan',
          nextNode: hasPrior ? 'node_2_imaging_assessment' : 'outcome_bt_0'
        }
      
      case 'node_2_imaging_assessment':
        // Enhanced volume analysis with full transparency and calculations
        const baselineFlair = parseFloat(patient?.data?.baseline_flair_volume || '0')
        const followupFlair = parseFloat(patient?.data?.followup_flair_volume || '0')
        const baselineEnh = parseFloat(patient?.data?.baseline_enhancement_volume || '0')
        const followupEnh = parseFloat(patient?.data?.followup_enhancement_volume || '0')
        
        // Create detailed calculations with transparency and correct bidirectional thresholds
        const flairAbsoluteChange = followupFlair - baselineFlair
        const enhAbsoluteChange = followupEnh - baselineEnh
        const flairPercentageChange = baselineFlair !== 0 ? ((followupFlair - baselineFlair) / baselineFlair) * 100 : 0
        const enhPercentageChange = baselineEnh !== 0 ? ((followupEnh - baselineEnh) / baselineEnh) * 100 : 0

        const calculations: CalculationStep[] = [
          createCalculation(
            'flair-percentage-change',
            'FLAIR Percentage Change',
            '((followupVolume - baselineVolume) / baselineVolume) × 100',
            {
              followupVolume: followupFlair,
              baselineVolume: baselineFlair
            },
            flairPercentageChange,
            '%',
            'Percentage change in FLAIR volume from baseline',
            flairPercentageChange < -10 ? { value: -10, operator: '<' } : 
            flairPercentageChange > 10 ? { value: 10, operator: '>' } : undefined
          ),
          createCalculation(
            'flair-absolute-significance',
            'FLAIR Absolute Change Significance',
            'abs(volumeChange) ≥ 1.0 mL',
            {
              volumeChange: flairAbsoluteChange,
              absoluteValue: Math.abs(flairAbsoluteChange),
              threshold: 1.0
            },
            Math.abs(flairAbsoluteChange),
            'mL',
            'Absolute change must be ≥1 mL (measurable disease = 1×1×1 cm)',
            { value: 1.0, operator: '>=' }
          ),
          createCalculation(
            'enh-percentage-change',
            'Enhancement Percentage Change',
            '((followupVolume - baselineVolume) / baselineVolume) × 100',
            {
              followupVolume: followupEnh,
              baselineVolume: baselineEnh
            },
            enhPercentageChange,
            '%',
            'Percentage change in enhancement volume from baseline',
            enhPercentageChange < -10 ? { value: -10, operator: '<' } : 
            enhPercentageChange > 10 ? { value: 10, operator: '>' } : undefined
          ),
          createCalculation(
            'enh-absolute-significance',
            'Enhancement Absolute Change Significance',
            'abs(volumeChange) ≥ 1.0 mL',
            {
              volumeChange: enhAbsoluteChange,
              absoluteValue: Math.abs(enhAbsoluteChange),
              threshold: 1.0
            },
            Math.abs(enhAbsoluteChange),
            'mL',
            'Absolute change must be ≥1 mL (measurable disease = 1×1×1 cm)',
            { value: 1.0, operator: '>=' }
          )
        ]
        
        const flairChange = flairPercentageChange
        const enhChange = enhPercentageChange
        
        // For significant change, must meet BOTH percentage AND absolute thresholds
        const flairImproved = flairChange < -10 && Math.abs(flairAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD
        const enhImproved = enhChange < -10 && Math.abs(enhAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD
        
        const flairWorsened = flairChange > 10 && Math.abs(flairAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD
        const enhWorsened = enhChange > 10 && Math.abs(enhAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD
        
        // BT-RADS assessment logic: improvement/stability/worsening with detailed criteria
        const criteria: DecisionCriteria[] = [
          {
            id: 'flair-improvement',
            condition: 'FLAIR improved by >10% AND absolute change ≥1 mL',
            value: `${flairChange.toFixed(1)}% (${Math.abs(flairAbsoluteChange).toFixed(2)} mL)`,
            threshold: '-10% AND 1 mL',
            operator: '<',
            met: flairImproved,
            reasoning: `FLAIR: ${flairChange.toFixed(1)}% change with ${Math.abs(flairAbsoluteChange).toFixed(2)} mL absolute change. ${
              flairChange < -10 ? 
                (Math.abs(flairAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD ? 
                  'Meets both percentage and measurable disease thresholds' : 
                  'Percentage threshold met but absolute change <1 mL (not measurable disease)') :
                'Does not meet percentage threshold'
            }`
          },
          {
            id: 'enh-improvement',
            condition: 'Enhancement improved by >10% AND absolute change ≥1 mL',
            value: `${enhChange.toFixed(1)}% (${Math.abs(enhAbsoluteChange).toFixed(2)} mL)`,
            threshold: '-10% AND 1 mL',
            operator: '<',
            met: enhImproved,
            reasoning: `Enhancement: ${enhChange.toFixed(1)}% change with ${Math.abs(enhAbsoluteChange).toFixed(2)} mL absolute change. ${
              enhChange < -10 ? 
                (Math.abs(enhAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD ? 
                  'Meets both percentage and measurable disease thresholds' : 
                  'Percentage threshold met but absolute change <1 mL (not measurable disease)') :
                'Does not meet percentage threshold'
            }`
          },
          {
            id: 'flair-progression',
            condition: 'FLAIR worsened by >10% AND absolute change ≥1 mL',
            value: `${flairChange.toFixed(1)}% (${Math.abs(flairAbsoluteChange).toFixed(2)} mL)`,
            threshold: '+10% AND 1 mL',
            operator: '>',
            met: flairWorsened,
            reasoning: `FLAIR: ${flairChange.toFixed(1)}% change with ${Math.abs(flairAbsoluteChange).toFixed(2)} mL absolute change. ${
              flairChange > 10 ? 
                (Math.abs(flairAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD ? 
                  'Meets both percentage and measurable disease thresholds' : 
                  'Percentage threshold met but absolute change <1 mL (not measurable disease)') :
                'Does not meet percentage threshold'
            }`
          },
          {
            id: 'enh-progression',
            condition: 'Enhancement worsened by >10% AND absolute change ≥1 mL',
            value: `${enhChange.toFixed(1)}% (${Math.abs(enhAbsoluteChange).toFixed(2)} mL)`,
            threshold: '+10% AND 1 mL',
            operator: '>',
            met: enhWorsened,
            reasoning: `Enhancement: ${enhChange.toFixed(1)}% change with ${Math.abs(enhAbsoluteChange).toFixed(2)} mL absolute change. ${
              enhChange > 10 ? 
                (Math.abs(enhAbsoluteChange) >= MEASURABLE_DISEASE_THRESHOLD ? 
                  'Meets both percentage and measurable disease thresholds' : 
                  'Percentage threshold met but absolute change <1 mL (not measurable disease)') :
                'Does not meet percentage threshold'
            }`
          }
        ]
        
        let assessment = 'unchanged'
        if (flairImproved || enhImproved) {
          assessment = 'improved'
        } else if (flairWorsened || enhWorsened) {
          assessment = 'worse'
        }
        
        // Alternative paths based on different thresholds
        const alternativePaths: AlternativePath[] = []
        if (assessment === 'unchanged') {
          if (flairChange < -5 || enhChange < -5) {
            alternativePaths.push({
              nodeId: 'node_3a_medications',
              label: 'Mild Improvement Pathway',
              reason: 'Could consider 5% threshold for improvement',
              wouldLeadTo: 'Medication analysis for mild improvement'
            })
          }
          if (flairChange > 5 || enhChange > 5) {
            alternativePaths.push({
              nodeId: 'node_4_time_since_xrt',
              label: 'Mild Progression Pathway', 
              reason: 'Could consider 5% threshold for progression',
              wouldLeadTo: 'Radiation timeline analysis for mild progression'
            })
          }
        }
        
        // Create decision point
        const decisionPoint: DecisionPoint = {
          id: `decision-${step.nodeId}`,
          nodeId: step.nodeId,
          label: 'Volume Change Assessment',
          description: 'Determine overall imaging assessment based on volume changes in FLAIR and enhancement',
          criteria,
          selectedPath: assessment === 'unchanged' ? 'Stable Disease (BT-2)' :
                       assessment === 'improved' ? 'Improvement Analysis' : 'Progression Analysis',
          alternativePaths,
          confidence: 95, // High confidence in volume calculations
          reasoning: `Assessment: ${assessment.toUpperCase()} based on FLAIR ${flairChange.toFixed(1)}% and Enhancement ${enhChange.toFixed(1)}% changes using 10% threshold per BT-RADS criteria`
        }
        
        // Create confidence assessment
        const confidence = createConfidenceData(
          95, // High evidence quality - quantitative measurements
          (baselineFlair > 0 && baselineEnh > 0) ? 100 : 75, // Data completeness
          100, // Perfect pattern matching for numbers
          90, // Clinical coherence
          `Volume analysis based on quantitative measurements with high precision. Both FLAIR and enhancement volumes available with clear percentage calculations.`,
          baselineFlair === 0 || baselineEnh === 0 ? ['Zero baseline volume may affect percentage calculation accuracy'] : [],
          []
        )
        
        // Create verification items
        const verificationItems: VerificationItem[] = [
          {
            id: `verify-calculations-${step.nodeId}`,
            category: 'calculation',
            description: 'Volume change calculations and threshold assessment',
            aiResult: {
              flairChange: flairChange.toFixed(2),
              enhChange: enhChange.toFixed(2),
              assessment,
              calculations: calculations.map(c => ({
                label: c.label,
                formula: c.formula,
                result: c.result,
                unit: c.unit
              }))
            }
          },
          {
            id: `verify-assessment-${step.nodeId}`,
            category: 'decision',
            description: 'Overall imaging assessment determination',
            aiResult: {
              assessment,
              reasoning: `FLAIR: ${flairChange.toFixed(1)}%, Enhancement: ${enhChange.toFixed(1)}% using 10% threshold`,
              nextNode: assessment === 'unchanged' ? 'outcome_bt_2' : 
                       assessment === 'improved' ? 'node_3a_medications' : 'node_4_time_since_xrt'
            }
          }
        ]
        
        return {
          ...step,
          status: 'completed',
          data: {
            assessment,
            flairChange,
            enhChange,
            flairVolume: `${baselineFlair} → ${followupFlair} mL`,
            enhVolume: `${baselineEnh} → ${followupEnh} mL`,
            flairAbsolute: (followupFlair - baselineFlair).toFixed(1),
            enhAbsolute: (followupEnh - baselineEnh).toFixed(1)
          },
          reasoning: `Volume Analysis: FLAIR ${flairChange < 0 ? 'decreased' : 'increased'} ${Math.abs(flairChange).toFixed(1)}% (${Math.abs(flairAbsoluteChange).toFixed(2)} mL), Enhancement ${enhChange < 0 ? 'decreased' : 'increased'} ${Math.abs(enhChange).toFixed(1)}% (${Math.abs(enhAbsoluteChange).toFixed(2)} mL). ${
            assessment === 'unchanged' && (Math.abs(flairChange) > 10 || Math.abs(enhChange) > 10) ?
              'Note: Percentage threshold met but absolute change <1 mL (below measurable disease threshold).' :
              assessment === 'improved' ? 'Both percentage (>10%) and measurable disease (≥1 mL) thresholds met.' :
              assessment === 'worse' ? 'Both percentage (>10%) and measurable disease (≥1 mL) thresholds met.' :
              'Within stability range (±10% OR <1 mL absolute change).'
          } Assessment: ${assessment.toUpperCase()}`,
          calculations,
          confidence,
          decisionPoint,
          verificationItems,
          nextNode: assessment === 'unchanged' ? 'outcome_bt_2' : 
                   assessment === 'improved' ? 'node_3a_medications' : 'node_4_time_since_xrt'
        }
      
      case 'node_3a_medications':
        // Enhanced medication extraction with comprehensive pattern matching and full transparency
        const clinicalNote = patient?.data?.clinical_note?.toLowerCase() || ''
        const originalNote = patient?.data?.clinical_note || ''
        
        // Avastin/Bevacizumab detection with dosage and timing context
        const avastinPatterns = [
          /avastin/gi, /bevacizumab/gi, /bev\b/gi, /anti-angiogenic/gi,
          /vegf\s*inhibitor/gi, /anti-vegf/gi
        ]
        const avastinPatternNames = ['Avastin', 'Bevacizumab', 'Bev abbreviation', 'Anti-angiogenic', 'VEGF inhibitor', 'Anti-VEGF']
        const onAvastin = avastinPatterns.some(pattern => pattern.test(clinicalNote))
        
        // Enhanced steroid detection with specific medications
        const steroidPatterns = [
          /dexamethasone/gi, /decadron/gi, /prednisone/gi, /prednisolone/gi,
          /methylprednisolone/gi, /steroid/gi, /corticosteroid/gi
        ]
        const steroidPatternNames = ['Dexamethasone', 'Decadron', 'Prednisone', 'Prednisolone', 'Methylprednisolone', 'Steroid (generic)', 'Corticosteroid']
        const onSteroids = steroidPatterns.some(pattern => pattern.test(clinicalNote))
        
        // Additional context analysis
        const contextPatterns = [
          /recent|start|initiat|increas|decreas|wean|taper/gi,
          /stable|continu|maintain|same\s*dose/gi
        ]
        const contextPatternNames = ['Recent changes', 'Stable dosing']
        const recentMedChange = contextPatterns[0].test(clinicalNote)
        const stableDose = contextPatterns[1].test(clinicalNote)
        
        // Create evidence from pattern matches
        const evidence: EvidenceItem[] = [
          ...createEvidence(originalNote, avastinPatterns, 'medication', avastinPatternNames),
          ...createEvidence(originalNote, steroidPatterns, 'medication', steroidPatternNames),
          ...createEvidence(originalNote, contextPatterns, 'temporal', contextPatternNames)
        ]
        
        // Extract medication mentions for detailed analysis
        const extractedMeds = clinicalNote.match(/(avastin|bevacizumab|dexamethasone|decadron|prednisone|steroid)/gi) || []
        
        // Decision logic prioritizing Avastin over steroids
        let medicationPath = 'neither'
        if (onAvastin) medicationPath = 'avastin'
        else if (onSteroids) medicationPath = 'steroids'
        
        // Create decision criteria for audit trail
        const medicationCriteria: DecisionCriteria[] = [
          {
            id: 'avastin-detected',
            condition: 'Avastin/Anti-angiogenic therapy detected',
            value: onAvastin,
            met: onAvastin,
            reasoning: `Found ${evidence.filter(e => e.category === 'medication' && avastinPatternNames.some(n => e.matchedPattern.includes(n.toLowerCase()))).length} Avastin-related patterns in clinical note`
          },
          {
            id: 'steroid-detected',
            condition: 'Corticosteroid therapy detected',
            value: onSteroids,
            met: onSteroids,
            reasoning: `Found ${evidence.filter(e => e.category === 'medication' && steroidPatternNames.some(n => e.matchedPattern.includes(n.toLowerCase()))).length} steroid-related patterns in clinical note`
          },
          {
            id: 'pathway-priority',
            condition: 'Avastin takes priority over steroids if both present',
            value: medicationPath,
            met: true,
            reasoning: onAvastin && onSteroids ? 'Both medications present - Avastin pathway selected per protocol' : 'Single medication type detected'
          }
        ]
        
        // Alternative paths
        const medicationAlternativePaths: AlternativePath[] = []
        if (onAvastin && !onSteroids) {
          medicationAlternativePaths.push({
            nodeId: 'node_3c_steroid_effects',
            label: 'Steroid Effects Analysis',
            reason: 'No steroid therapy detected',
            wouldLeadTo: 'BT-1a or BT-1b based on steroid assessment'
          })
        } else if (onSteroids && !onAvastin) {
          medicationAlternativePaths.push({
            nodeId: 'node_3b_avastin_response',
            label: 'Avastin Response Analysis',
            reason: 'No anti-angiogenic therapy detected',
            wouldLeadTo: 'BT-1a or BT-1b based on Avastin response'
          })
        }
        if (!onAvastin && !onSteroids) {
          medicationAlternativePaths.push(
            {
              nodeId: 'node_3b_avastin_response',
              label: 'Avastin Response Analysis',
              reason: 'No anti-angiogenic therapy detected',
              wouldLeadTo: 'BT-1a (true improvement)'
            },
            {
              nodeId: 'node_3c_steroid_effects',
              label: 'Steroid Effects Analysis',
              reason: 'No steroid therapy detected',
              wouldLeadTo: 'BT-1a (true improvement)'
            }
          )
        }
        
        // Create decision point for audit trail
        const medicationDecisionPoint: DecisionPoint = {
          id: `decision-${step.nodeId}`,
          nodeId: step.nodeId,
          label: 'Medication Pathway Selection',
          description: 'Determine which medication pathway to follow based on detected therapies',
          criteria: medicationCriteria,
          selectedPath: medicationPath === 'avastin' ? 'Avastin Response Analysis' :
                       medicationPath === 'steroids' ? 'Steroid Effects Analysis' : 'True Improvement (No Confounders)',
          alternativePaths: medicationAlternativePaths,
          confidence: evidence.length > 0 ? 85 : 60,
          reasoning: `Selected ${medicationPath} pathway based on clinical note analysis. Found ${evidence.length} relevant evidence items.`
        }
        
        // Enhanced reasoning with clinical context
        let medAnalysis = ''
        if (onAvastin && onSteroids) {
          medAnalysis = `Both Avastin and steroids identified. Prioritizing Avastin pathway due to stronger anti-tumor effect. ${recentMedChange ? 'Recent medication changes noted.' : 'Stable dosing regimen.'}`
        } else if (onAvastin) {
          medAnalysis = `Avastin/Bevacizumab therapy detected. Anti-angiogenic treatment can cause apparent volume reduction independent of tumor response. ${stableDose ? 'Stable dosing suggests established treatment effect.' : 'Dosing changes may affect interpretation.'}`
        } else if (onSteroids) {
          medAnalysis = `Corticosteroid therapy identified (${extractedMeds.join(', ')}). Steroids reduce peritumoral edema and can cause apparent improvement in FLAIR signal. ${recentMedChange ? 'Recent steroid changes may confound assessment.' : ''}`
        } else {
          medAnalysis = 'No significant anti-angiogenic agents or high-dose steroids identified. Improvement likely represents true tumor response to primary therapy.'
        }
        
        // Create confidence assessment
        const medicationConfidence = createConfidenceData(
          evidence.length > 2 ? 90 : evidence.length > 0 ? 70 : 40,
          extractedMeds.length > 0 ? 95 : 80,
          onAvastin || onSteroids ? 90 : 60,
          85,
          `Medication analysis based on ${evidence.length} evidence items and ${extractedMeds.length} extracted medication mentions`,
          evidence.length === 0 ? ['No explicit medication patterns found - relying on general clinical context'] : [],
          onAvastin && onSteroids ? ['Could consider combination therapy effects'] : []
        )
        
        // Create verification items for expert review
        const medicationVerificationItems: VerificationItem[] = [
          {
            id: `verify-medications-${step.nodeId}`,
            category: 'interpretation',
            description: 'Medication detection and pathway selection',
            aiResult: {
              onAvastin,
              onSteroids,
              medicationPath,
              extractedMeds,
              selectedPathway: medicationPath === 'avastin' ? 'node_3b_avastin_response' :
                              medicationPath === 'steroids' ? 'node_3c_steroid_effects' : 'outcome_bt_1a'
            }
          }
        ]
        
        return {
          ...step,
          status: 'completed',
          data: {
            onAvastin,
            onSteroids,
            medicationPath,
            extractedMeds,
            recentMedChange,
            stableDose,
            clinicalContext: onAvastin && onSteroids ? 'Combination therapy' : 
                           onAvastin ? 'Anti-angiogenic therapy' :
                           onSteroids ? 'Corticosteroid therapy' : 'Standard therapy'
          },
          reasoning: medAnalysis,
          evidence,
          confidence: medicationConfidence,
          decisionPoint: medicationDecisionPoint,
          verificationItems: medicationVerificationItems,
          nextNode: medicationPath === 'avastin' ? 'node_3b_avastin_response' :
                   medicationPath === 'steroids' ? 'node_3c_steroid_effects' : 'outcome_bt_1a'
        }
      
      case 'node_4_time_since_xrt':
        // Enhanced radiation timeline analysis with comprehensive pattern matching
        const clinicalNoteRad = patient?.data?.clinical_note?.toLowerCase() || ''
        const originalNoteRad = patient?.data?.clinical_note || ''
        
        // Enhanced radiation detection patterns with date focus
        // Date range patterns to capture start and end dates
        const radiationDateRangePatterns = [
          /radiation.*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[-–]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
          /(?:xrt|radiotherapy).*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[-–]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
          /(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[-–]\s*(\d{1,2}\/\d{1,2}\/\d{2,4}).*?(?:radiation|xrt|radiotherapy)/gi
        ]
        
        // Single date patterns as fallback
        const radiationDatePatterns = [
          /radiation.*?(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
          /(?:xrt|radiotherapy).*?(\d{1,2}\/\d{1,2}\/\d{2,4})/gi,
          /(\d{1,2}\/\d{1,2}\/\d{2,4}).*?radiation/gi,
          /(\d{1,2}\/\d{1,2}\/\d{2,4}).*?(?:xrt|radiotherapy)/gi
        ]
        
        const radiationPatterns = [
          /radiation\s*therapy/gi, 
          /radiotherapy/gi, 
          /\bxrt\b/gi,  // Word boundaries to avoid matching within words
          /\brt\b/gi,   // Word boundaries to avoid matching "Robert" etc
          /stereotactic\s*(?:radio|radiation|radiosurgery)/gi,  // Only radiation-related stereotactic
          /gamma\s*knife/gi, 
          /cyber\s*knife/gi,
          /fractionated\s*radiation/gi,  // More specific to radiation
          /hypofractionated\s*radiation/gi,  // More specific to radiation
          /radiosurgery/gi,
          ...radiationDateRangePatterns,  // Include date range patterns first
          ...radiationDatePatterns  // Include single date patterns as fallback
        ]
        
        const radiationPatternNames = [
          'Radiation therapy', 'Radiotherapy', 'XRT', 'RT', 
          'Stereotactic radiation', 'Gamma Knife', 'CyberKnife',
          'Fractionated radiation', 'Hypofractionated radiation', 'Radiosurgery',
          'Radiation with date range', 'XRT/Radiotherapy with date range', 'Date range before radiation',
          'Radiation with date', 'XRT/Radiotherapy with date', 'Date before radiation', 'Date before XRT/radiotherapy'
        ]
        const radiationMentioned = radiationPatterns.some(pattern => pattern.test(clinicalNoteRad))
        
        // Look for temporal indicators in clinical notes
        const recentRadKeywords = /recent|days?\s*ago|weeks?\s*ago|month\s*ago|just\s*completed|finishing/gi
        const distantRadKeywords = /months?\s*ago|years?\s*ago|remote|distant|prior|previous/gi
        
        const hasRecentIndicators = recentRadKeywords.test(clinicalNoteRad)
        const hasDistantIndicators = distantRadKeywords.test(clinicalNoteRad)
        
        // Create evidence items for radiation patterns
        const radiationEvidence = createEvidence(
          originalNoteRad, 
          radiationPatterns, 
          'radiation',
          radiationPatternNames
        )
        
        // Create evidence for temporal indicators
        const temporalPatterns = [recentRadKeywords, distantRadKeywords]
        const temporalPatternNames = ['Recent indicators', 'Distant indicators']
        const temporalEvidence = createEvidence(
          originalNoteRad,
          temporalPatterns,
          'temporal',
          temporalPatternNames
        )
        
        // Combine all evidence
        const evidenceRad = [...radiationEvidence, ...temporalEvidence]
        
        // Try to extract actual radiation dates
        let extractedRadiationDate: Date | null = null
        
        // First try to find date ranges (use end date)
        for (const pattern of radiationDateRangePatterns) {
          const match = originalNoteRad.match(pattern)
          if (match && match[2]) {  // match[2] is the end date in the range
            try {
              const testDate = new Date(match[2])
              // Check if date is valid
              if (!isNaN(testDate.getTime())) {
                extractedRadiationDate = testDate
                break
              }
            } catch (e) {
              // Invalid date format, continue
            }
          }
        }
        
        // If no date range found, try single dates
        if (!extractedRadiationDate) {
          for (const pattern of radiationDatePatterns) {
            const match = originalNoteRad.match(pattern)
            if (match && match[1]) {
              try {
                const testDate = new Date(match[1])
                // Check if date is valid
                if (!isNaN(testDate.getTime())) {
                  extractedRadiationDate = testDate
                  break
                }
              } catch (e) {
                // Invalid date format, continue
              }
            }
          }
        }
        
        // Enhanced timeline estimation based on clinical context
        let daysSinceXRT: number
        let confidenceLevel: string
        
        // If we have an actual radiation date and a follow-up date, calculate precisely
        if (extractedRadiationDate && patient?.data?.followup_date) {
          const followupDate = new Date(patient.data.followup_date)
          daysSinceXRT = Math.floor((followupDate.getTime() - extractedRadiationDate.getTime()) / (1000 * 60 * 60 * 24))
          confidenceLevel = 'Very High - extracted exact radiation date'
        } else if (hasRecentIndicators && !hasDistantIndicators) {
          daysSinceXRT = 45 // Recent radiation
          confidenceLevel = 'High - recent temporal indicators'
        } else if (hasDistantIndicators && !hasRecentIndicators) {
          daysSinceXRT = 150 // Distant radiation
          confidenceLevel = 'High - distant temporal indicators'
        } else if (radiationMentioned) {
          // Try to extract specific timeframe mentions
          const weekMatch = clinicalNoteRad.match(/(\d+)\s*weeks?\s*ago/i)
          const monthMatch = clinicalNoteRad.match(/(\d+)\s*months?\s*ago/i)
          
          if (weekMatch) {
            daysSinceXRT = parseInt(weekMatch[1]) * 7
            confidenceLevel = 'High - specific timeframe extracted'
          } else if (monthMatch) {
            daysSinceXRT = parseInt(monthMatch[1]) * 30
            confidenceLevel = 'High - specific timeframe extracted'
          } else {
            daysSinceXRT = 90 // Default assumption if radiation mentioned but timeline unclear
            confidenceLevel = 'Medium - radiation mentioned but timeline unclear'
          }
        } else {
          daysSinceXRT = 180 // No radiation mentioned, assume distant or no prior RT
          confidenceLevel = 'Low - no radiation therapy mentioned'
        }
        
        const isRecent = daysSinceXRT < 90
        
        // Enhanced clinical reasoning
        let radiationAnalysis = ''
        if (isRecent) {
          radiationAnalysis = `Recent radiation therapy (${daysSinceXRT} days ago). Changes likely represent treatment effect including inflammation, edema, or pseudoprogression rather than true tumor progression. Treatment-related changes typically peak at 1-3 months post-radiation.`
        } else {
          radiationAnalysis = `Distant or no recent radiation therapy (${daysSinceXRT} days). Changes less likely to be treatment-related and more concerning for true tumor progression. Late radiation effects are uncommon beyond 3 months.`
        }
        
        return {
          ...step,
          status: 'completed',
          data: {
            daysSinceXRT,
            isRecent,
            radiationMentioned,
            hasRecentIndicators,
            hasDistantIndicators,
            confidenceLevel,
            extractedRadiationDate: extractedRadiationDate && !isNaN(extractedRadiationDate.getTime()) 
              ? extractedRadiationDate.toISOString().split('T')[0] 
              : null,
            timeCategory: isRecent ? '< 90 days (Recent)' : '≥ 90 days (Distant)',
            radiationType: clinicalNoteRad.includes('stereotactic') && clinicalNoteRad.includes('radio') ? 'Stereotactic' :
                          clinicalNoteRad.includes('gamma') ? 'Gamma Knife' :
                          clinicalNoteRad.includes('cyber') ? 'CyberKnife' : 
                          radiationMentioned ? 'Standard RT' : 'None detected'
          },
          reasoning: radiationAnalysis,
          evidence: evidenceRad,
          nextNode: isRecent ? 'outcome_bt_3a' : 'node_5_what_is_worse'
        }
      
      case 'node_5_what_is_worse':
        // Enhanced component analysis with refined thresholds and mixed pattern detection
        const flairChangePercent = parseFloat(patient?.data?.flair_change_percentage || '0')
        const enhChangePercent = parseFloat(patient?.data?.enhancement_change_percentage || '0')
        
        // Absolute volume changes for context
        const flairAbsChange = parseFloat(patient?.data?.followup_flair_volume || '0') - 
                              parseFloat(patient?.data?.baseline_flair_volume || '0')
        const enhAbsChange = parseFloat(patient?.data?.followup_enhancement_volume || '0') - 
                            parseFloat(patient?.data?.baseline_enhancement_volume || '0')
        
        // Enhanced threshold analysis - requires both percentage AND absolute thresholds
        const flairWorse = flairChangePercent > 15 && Math.abs(flairAbsChange) >= MEASURABLE_DISEASE_THRESHOLD
        const enhWorse = enhChangePercent > 10 && Math.abs(enhAbsChange) >= MEASURABLE_DISEASE_THRESHOLD
        
        // Mixed pattern analysis - important for BT-RADS classification
        const isMixedPattern = (flairWorse && !enhWorse) || (!flairWorse && enhWorse)
        const isBothWorse = flairWorse && enhWorse
        const isNeitherWorse = !flairWorse && !enhWorse
        
        let componentAssessment: string
        let clinicalSignificance: string
        
        if (isBothWorse) {
          componentAssessment = 'both'
          clinicalSignificance = 'Concordant progression - both FLAIR and enhancement increased, highly concerning'
        } else if (isMixedPattern) {
          componentAssessment = 'single'
          if (flairWorse && !enhWorse) {
            clinicalSignificance = 'FLAIR-only progression - may represent infiltrative growth or treatment effect'
          } else {
            clinicalSignificance = 'Enhancement-only progression - may represent increased vascularity or breakdown of blood-brain barrier'
          }
        } else {
          componentAssessment = 'stable'
          clinicalSignificance = 'No significant component progression detected - may represent measurement variability'
        }
        
        // Enhanced reasoning with clinical context
        const componentReasoning = `Component analysis reveals ${componentAssessment === 'both' ? 'concordant progression' : componentAssessment === 'single' ? 'mixed pattern' : 'no significant progression'}.
        
FLAIR: ${flairChangePercent.toFixed(1)}% change (${flairAbsChange > 0 ? '+' : ''}${flairAbsChange.toFixed(1)} mL) - ${
  flairWorse ? 'SIGNIFICANT INCREASE (>15% and ≥1 mL)' : 
  flairChangePercent > 15 ? 'Percentage increase but <1 mL (not measurable)' : 
  'stable/decreased'
}
Enhancement: ${enhChangePercent.toFixed(1)}% change (${enhAbsChange > 0 ? '+' : ''}${enhAbsChange.toFixed(1)} mL) - ${
  enhWorse ? 'SIGNIFICANT INCREASE (>10% and ≥1 mL)' : 
  enhChangePercent > 10 ? 'Percentage increase but <1 mL (not measurable)' : 
  'stable/decreased'
}

Clinical significance: ${clinicalSignificance}`
        
        return {
          ...step,
          status: 'completed',
          data: {
            flairWorse,
            enhWorse,
            componentAssessment,
            flairChange: flairChangePercent,
            enhChange: enhChangePercent,
            flairAbsChange,
            enhAbsChange,
            isMixedPattern,
            isBothWorse,
            clinicalSignificance,
            dominantComponent: Math.abs(flairChangePercent) > Math.abs(enhChangePercent) ? 'FLAIR' : 'Enhancement'
          },
          reasoning: componentReasoning,
          nextNode: componentAssessment === 'single' ? 'outcome_bt_3b' : 
                   componentAssessment === 'both' ? 'node_6_how_much_worse' : 'outcome_bt_2'
        }
      
      case 'node_6_how_much_worse':
        // Enhanced extent analysis with multiple thresholds and clinical context
        const flairPercentAbs = Math.abs(parseFloat(patient?.data?.flair_change_percentage || '0'))
        const enhPercentAbs = Math.abs(parseFloat(patient?.data?.enhancement_change_percentage || '0'))
        const flairPercent = parseFloat(patient?.data?.flair_change_percentage || '0')
        const enhPercent = parseFloat(patient?.data?.enhancement_change_percentage || '0')
        
        // Multiple threshold analysis following clinical guidelines
        const maxChange = Math.max(flairPercentAbs, enhPercentAbs)
        const minChange = Math.min(flairPercentAbs, enhPercentAbs)
        
        // BT-RADS specific thresholds
        const isHighlySignificant = maxChange > 40  // >40% = Definitive progression
        const isSignificant = maxChange > 25        // >25% = Likely progression
        const isModerate = maxChange > 15           // >15% = Possible progression
        
        // Volume-based analysis
        const flairAbsChangeExtent = parseFloat(patient?.data?.followup_flair_volume || '0') - 
                                    parseFloat(patient?.data?.baseline_flair_volume || '0')
        const enhAbsChangeExtent = parseFloat(patient?.data?.followup_enhancement_volume || '0') - 
                                  parseFloat(patient?.data?.baseline_enhancement_volume || '0')
        const maxAbsChange = Math.max(Math.abs(flairAbsChangeExtent), Math.abs(enhAbsChangeExtent))
        
        // Clinical interpretation
        let extentCategory: string
        let clinicalInterpretation: string
        let riskLevel: string
        
        if (isHighlySignificant) {
          extentCategory = 'Massive increase'
          clinicalInterpretation = 'Dramatic volume increase consistent with aggressive tumor progression. Immediate clinical intervention required.'
          riskLevel = 'Very High'
        } else if (isSignificant) {
          extentCategory = 'Significant increase'
          clinicalInterpretation = 'Substantial volume increase highly suspicious for tumor progression. Progressive pattern assessment needed.'
          riskLevel = 'High'
        } else if (isModerate) {
          extentCategory = 'Moderate increase'
          clinicalInterpretation = 'Moderate volume increase of uncertain significance. Clinical correlation and progressive pattern analysis essential.'
          riskLevel = 'Moderate'
        } else {
          extentCategory = 'Mild increase'
          clinicalInterpretation = 'Minimal volume increase may represent measurement variability, treatment effect, or early progression.'
          riskLevel = 'Low-Moderate'
        }
        
        // Enhanced reasoning
        const extentReasoning = `Quantitative extent analysis reveals ${extentCategory.toLowerCase()}.

Volume Changes:
• FLAIR: ${flairPercent > 0 ? '+' : ''}${flairPercent.toFixed(1)}% (${flairAbsChangeExtent > 0 ? '+' : ''}${flairAbsChangeExtent.toFixed(1)} mL)
• Enhancement: ${enhPercent > 0 ? '+' : ''}${enhPercent.toFixed(1)}% (${enhAbsChangeExtent > 0 ? '+' : ''}${enhAbsChangeExtent.toFixed(1)} mL)
• Maximum change: ${maxChange.toFixed(1)}%
• Total absolute change: ${maxAbsChange.toFixed(1)} mL

Risk Assessment: ${riskLevel} risk for tumor progression
${clinicalInterpretation}`
        
        // Decision logic: >25% goes to BT-4, otherwise needs progressive assessment
        const directToBT4 = isSignificant
        
        return {
          ...step,
          status: 'completed',
          data: {
            flairPercent: flairPercentAbs,
            enhPercent: enhPercentAbs,
            maxChange,
            minChange,
            flairAbsChange: flairAbsChangeExtent,
            enhAbsChange: enhAbsChangeExtent,
            maxAbsChange,
            isHighlySignificant,
            isSignificant,
            isModerate,
            extentCategory,
            riskLevel,
            clinicalInterpretation,
            threshold: '25% (BT-RADS standard)',
            secondaryThreshold: '40% (highly suspicious)'
          },
          reasoning: extentReasoning,
          nextNode: directToBT4 ? 'outcome_bt_4' : 'node_7_progressive'
        }
      
      case 'node_7_progressive':
        // Enhanced progressive pattern analysis with comprehensive clinical assessment
        const clinicalNoteProg = patient?.data?.clinical_note?.toLowerCase() || ''
        
        // Progressive disease indicators
        const progressiveKeywords = [
          /progressive/gi, /progression/gi, /progressing/gi, /worsening/gi, /worsen/gi,
          /increasing/gi, /enlarging/gi, /expanding/gi, /growing/gi, /accelerating/gi
        ]
        const hasProgressivePattern = progressiveKeywords.some(pattern => pattern.test(clinicalNoteProg))
        
        // Temporal progression indicators
        const temporalProgression = [
          /over\s+time/gi, /serial\s+imaging/gi, /compared\s+to\s+prior/gi,
          /interval\s+change/gi, /since\s+last/gi, /consecutive/gi
        ]
        const hasTemporalProgression = temporalProgression.some(pattern => pattern.test(clinicalNoteProg))
        
        // Stability indicators (negative evidence)
        const stabilityKeywords = [
          /stable/gi, /unchanged/gi, /no\s+change/gi, /similar/gi, /consistent/gi,
          /plateau/gi, /stationary/gi
        ]
        const hasStabilityIndications = stabilityKeywords.some(pattern => pattern.test(clinicalNoteProg))
        
        // Clinical symptoms progression
        const symptomProgression = [
          /neurologic\s+decline/gi, /worsening\s+symptoms/gi, /new\s+symptoms/gi,
          /increased\s+seizures/gi, /cognitive\s+decline/gi, /functional\s+decline/gi
        ]
        const hasClinicalProgression = symptomProgression.some(pattern => pattern.test(clinicalNoteProg))
        
        // Prior progression history
        const priorProgressionIndicators = [
          /previous\s+progression/gi, /prior\s+progression/gi, /history\s+of\s+progression/gi,
          /recurrent/gi, /relapse/gi
        ]
        const hasPriorProgression = priorProgressionIndicators.some(pattern => pattern.test(clinicalNoteProg))
        
        // Treatment response context
        const treatmentResponse = [
          /refractory/gi, /resistant/gi, /failed\s+treatment/gi, /no\s+response/gi,
          /treatment\s+failure/gi
        ]
        const isTreatmentRefractory = treatmentResponse.some(pattern => pattern.test(clinicalNoteProg))
        
        // Composite progressive assessment
        const progressiveEvidence = [
          hasProgressivePattern,
          hasTemporalProgression,
          hasClinicalProgression,
          isTreatmentRefractory
        ].filter(Boolean).length
        
        const stabilityEvidence = hasStabilityIndications ? 1 : 0
        const isFirstTimeWorse = !hasPriorProgression
        
        // Decision logic: high progressive evidence suggests BT-4
        const strongProgressiveEvidence = progressiveEvidence >= 2 && stabilityEvidence === 0
        const moderateProgressiveEvidence = progressiveEvidence >= 1 && !hasStabilityIndications
        
        // Enhanced clinical reasoning
        let progressiveAnalysis = `Progressive pattern assessment based on clinical documentation:

Evidence for Progression:
• Progressive imaging pattern: ${hasProgressivePattern ? '✓ Documented' : '✗ Not documented'}
• Temporal progression: ${hasTemporalProgression ? '✓ Serial changes noted' : '✗ No temporal context'}
• Clinical progression: ${hasClinicalProgression ? '✓ Symptomatic worsening' : '✗ No clinical decline'}
• Treatment resistance: ${isTreatmentRefractory ? '✓ Refractory disease' : '✗ Treatment responsive'}

Evidence against Progression:
• Stability indicators: ${hasStabilityIndications ? '⚠ Some stability noted' : '✓ No stability claims'}
• Prior progression: ${hasPriorProgression ? '⚠ Previous progression history' : '✓ First occurrence'}

Conclusion: ${strongProgressiveEvidence ? 'Strong progressive pattern - highly suspicious (BT-4)' : 
             moderateProgressiveEvidence ? 'Moderate concern for progression - favor progression (BT-3c)' : 
             'Insufficient evidence for definitive progression - favor progression but less certain (BT-3c)'}`
        
        return {
          ...step,
          status: 'completed',
          data: {
            hasProgressivePattern,
            hasTemporalProgression,
            hasClinicalProgression,
            hasStabilityIndications,
            hasPriorProgression,
            isTreatmentRefractory,
            isFirstTimeWorse,
            progressiveEvidence,
            stabilityEvidence,
            strongProgressiveEvidence,
            moderateProgressiveEvidence,
            clinicalContext: strongProgressiveEvidence ? 'Strong Progressive Pattern' :
                           moderateProgressiveEvidence ? 'Moderate Progressive Pattern' :
                           'Weak Progressive Pattern'
          },
          reasoning: progressiveAnalysis,
          nextNode: strongProgressiveEvidence ? 'outcome_bt_4' : 'outcome_bt_3c'
        }
      
      case 'node_3b_avastin_response':
        // Enhanced Avastin response pattern analysis
        const clinicalNoteAvastin = patient?.data?.clinical_note?.toLowerCase() || ''
        
        // Timeline analysis for Avastin response
        const firstStudyIndicators = [
          /first\s+study/gi, /initial\s+response/gi, /started\s+avastin/gi, /beginning\s+avastin/gi,
          /recently\s+started/gi, /new\s+avastin/gi, /first\s+imaging/gi
        ]
        const sustainedResponseIndicators = [
          /sustained\s+response/gi, /continued\s+response/gi, /ongoing\s+response/gi,
          /maintained\s+improvement/gi, /durable\s+response/gi, /long-term\s+response/gi,
          /months\s+on\s+avastin/gi, /established\s+response/gi
        ]
        
        const isFirstStudyOnAvastin = firstStudyIndicators.some(pattern => pattern.test(clinicalNoteAvastin)) ||
                                     (!sustainedResponseIndicators.some(pattern => pattern.test(clinicalNoteAvastin)) &&
                                      !clinicalNoteAvastin.includes('month'))
        
        // Avastin-specific response patterns
        const avastinEffectIndicators = [
          /anti-angiogenic\s+effect/gi, /vascular\s+response/gi, /decreased\s+perfusion/gi,
          /reduced\s+enhancement/gi, /pseudoresponse/gi, /avastin\s+effect/gi
        ]
        const hasAvastinEffect = avastinEffectIndicators.some(pattern => pattern.test(clinicalNoteAvastin))
        
        // True tumor response indicators
        const trueResponseIndicators = [
          /true\s+response/gi, /tumor\s+shrinkage/gi, /cytotoxic\s+effect/gi,
          /genuine\s+response/gi, /real\s+improvement/gi, /actual\s+response/gi
        ]
        const hasTrueResponse = trueResponseIndicators.some(pattern => pattern.test(clinicalNoteAvastin))
        
        // Clinical context assessment
        const durationContext = clinicalNoteAvastin.includes('week') ? 'Recent initiation (weeks)' :
                               clinicalNoteAvastin.includes('month') ? 'Established therapy (months)' :
                               'Timeline unclear'
        
        // Enhanced decision logic
        const likelyMedicationEffect = isFirstStudyOnAvastin || hasAvastinEffect
        const likelyTrueResponse = !isFirstStudyOnAvastin && (hasTrueResponse || 
                                  sustainedResponseIndicators.some(pattern => pattern.test(clinicalNoteAvastin)))
        
        // Clinical interpretation
        let avastinAnalysis = ''
        if (likelyMedicationEffect && !likelyTrueResponse) {
          avastinAnalysis = `Avastin medication effect likely (BT-1b pathway). ${durationContext}. Anti-angiogenic agents can cause apparent volume reduction through vascular normalization and decreased permeability, independent of true anti-tumor activity. ${hasAvastinEffect ? 'Specific anti-angiogenic effects documented.' : 'Timeline suggests initial treatment response.'}`
        } else if (likelyTrueResponse) {
          avastinAnalysis = `True tumor response likely (BT-1a pathway). ${durationContext}. Sustained improvement beyond initial anti-angiogenic effect suggests genuine tumor response to therapy. ${hasTrueResponse ? 'True response pattern documented.' : 'Sustained improvement pattern consistent with tumor response.'}`
        } else {
          avastinAnalysis = `Mixed or unclear Avastin response pattern. Defaulting to medication effect pathway (BT-1b) for conservative interpretation. ${durationContext}.`
        }
        
        return {
          ...step,
          status: 'completed',
          data: {
            isFirstStudyOnAvastin,
            hasAvastinEffect,
            hasTrueResponse,
            likelyMedicationEffect,
            likelyTrueResponse,
            durationContext,
            treatmentHistory: isFirstStudyOnAvastin ? 'First study on Avastin' : 'Established Avastin therapy',
            responseType: likelyMedicationEffect && !likelyTrueResponse ? 'Medication Effect' :
                         likelyTrueResponse ? 'True Tumor Response' : 'Indeterminate'
          },
          reasoning: avastinAnalysis,
          nextNode: likelyMedicationEffect && !likelyTrueResponse ? 'outcome_bt_1b' : 'outcome_bt_1a'
        }
      
      case 'node_3c_steroid_effects':
        // Enhanced steroid effects analysis with comprehensive assessment
        const clinicalNoteSteroid = patient?.data?.clinical_note?.toLowerCase() || ''
        
        // Enhanced steroid detection with dosage context
        const highDoseSteroids = [
          /high.*dose.*steroid/gi, /high.*dose.*dexamethasone/gi, 
          /4\s*mg.*dexamethasone/gi, /8\s*mg.*dexamethasone/gi,
          /pulse.*steroid/gi, /loading.*dose/gi
        ]
        const lowDoseSteroids = [
          /low.*dose.*steroid/gi, /maintenance.*steroid/gi,
          /2\s*mg.*dexamethasone/gi, /1\s*mg.*dexamethasone/gi,
          /tapering/gi, /weaning/gi
        ]
        
        const hasHighDoseSteroids = highDoseSteroids.some(pattern => pattern.test(clinicalNoteSteroid))
        const hasLowDoseSteroids = lowDoseSteroids.some(pattern => pattern.test(clinicalNoteSteroid))
        
        // Steroid timing analysis
        const recentSteroidStart = [
          /started.*steroid/gi, /initiated.*steroid/gi, /began.*dexamethasone/gi,
          /recent.*steroid/gi, /new.*steroid/gi
        ]
        const establishedSteroidUse = [
          /chronic.*steroid/gi, /long.*term.*steroid/gi, /stable.*dose/gi,
          /continued.*steroid/gi, /ongoing.*steroid/gi
        ]
        
        const hasRecentSteroidStart = recentSteroidStart.some(pattern => pattern.test(clinicalNoteSteroid))
        const hasEstablishedSteroidUse = establishedSteroidUse.some(pattern => pattern.test(clinicalNoteSteroid))
        
        // Steroid-specific effects on imaging
        const steroidEffectIndicators = [
          /reduced.*edema/gi, /decreased.*mass.*effect/gi, /improved.*midline/gi,
          /steroid.*response/gi, /anti.*inflammatory.*effect/gi,
          /decreased.*flair/gi, /steroid.*effect/gi
        ]
        const hasDocumentedSteroidEffect = steroidEffectIndicators.some(pattern => pattern.test(clinicalNoteSteroid))
        
        // True tumor response indicators
        const tumorResponseIndicators = [
          /tumor.*shrinkage/gi, /decreased.*enhancement/gi, /genuine.*response/gi,
          /true.*improvement/gi, /cytotoxic.*effect/gi
        ]
        const hasTumorResponse = tumorResponseIndicators.some(pattern => pattern.test(clinicalNoteSteroid))
        
        // Clinical reasoning algorithm
        let likelySteroidsEffect: boolean
        let confidenceLevelSteroid: string
        let steroidImpact: string
        
        if (hasHighDoseSteroids || (hasRecentSteroidStart && !hasTumorResponse)) {
          likelySteroidsEffect = true
          confidenceLevelSteroid = 'High'
          steroidImpact = 'High-dose or recently initiated steroids - strong confounding effect'
        } else if (hasDocumentedSteroidEffect || (hasLowDoseSteroids && hasRecentSteroidStart)) {
          likelySteroidsEffect = true
          confidenceLevelSteroid = 'Moderate'
          steroidImpact = 'Documented steroid effects - moderate confounding'
        } else if (hasEstablishedSteroidUse && !hasTumorResponse) {
          likelySteroidsEffect = false
          confidenceLevelSteroid = 'Moderate'
          steroidImpact = 'Established steroid use - minimal additional effect expected'
        } else if (hasTumorResponse) {
          likelySteroidsEffect = false
          confidenceLevelSteroid = 'High'
          steroidImpact = 'True tumor response documented - steroid effect unlikely'
        } else {
          likelySteroidsEffect = clinicalNoteSteroid.includes('steroid') || clinicalNoteSteroid.includes('dexamethasone')
          confidenceLevelSteroid = 'Low'
          steroidImpact = 'Steroid use noted but impact unclear'
        }
        
        // Enhanced clinical reasoning
        const steroidAnalysis = `Steroid effect assessment on apparent tumor improvement:

Steroid Context:
• High-dose steroids: ${hasHighDoseSteroids ? '✓ High-dose therapy detected' : '✗ No high-dose therapy'}
• Recent steroid initiation: ${hasRecentSteroidStart ? '✓ Recently started' : '✗ Not recently started'}
• Documented steroid effects: ${hasDocumentedSteroidEffect ? '✓ Anti-inflammatory effects noted' : '✗ No specific effects documented'}
• True tumor response: ${hasTumorResponse ? '✓ Genuine tumor response documented' : '✗ No clear tumor response'}

Clinical Interpretation (${confidenceLevelSteroid} confidence): ${steroidImpact}

Conclusion: ${likelySteroidsEffect ? 
  'Improvement likely confounded by steroid effects - assign BT-1b (possible medication effect)' : 
  'Improvement likely represents true tumor response - assign BT-1a (improved)'}`
        
        return {
          ...step,
          status: 'completed',
          data: {
            likelySteroidsEffect,
            hasHighDoseSteroids,
            hasLowDoseSteroids,
            hasRecentSteroidStart,
            hasEstablishedSteroidUse,
            hasDocumentedSteroidEffect,
            hasTumorResponse,
            confidenceLevel: confidenceLevelSteroid,
            steroidImpact,
            steroidDosage: hasHighDoseSteroids ? 'High-dose' : hasLowDoseSteroids ? 'Low-dose' : 'Unspecified',
            steroidTiming: hasRecentSteroidStart ? 'Recent initiation' : hasEstablishedSteroidUse ? 'Established use' : 'Unclear'
          },
          reasoning: steroidAnalysis,
          nextNode: likelySteroidsEffect ? 'outcome_bt_1b' : 'outcome_bt_1a'
        }
      
      case 'outcome_bt_0':
        return {
          ...step,
          status: 'completed',
          btradsScore: '0',
          reasoning: 'BT-RADS 0: Incomplete assessment. No suitable prior imaging available for comparison.',
          data: { 
            finalScore: 'BT-0', 
            category: 'Baseline/Incomplete',
            clinicalAction: 'Obtain baseline imaging for future comparison',
            followUp: 'Establish baseline, repeat imaging per clinical protocol'
          }
        }
        
      case 'outcome_bt_1a':
        return {
          ...step,
          status: 'completed',
          btradsScore: '1a',
          reasoning: 'BT-RADS 1a: Improvement. Decreased tumor burden without medication confounders.',
          data: { 
            finalScore: 'BT-1a', 
            category: 'Improved',
            clinicalAction: 'Continue current treatment regimen',
            followUp: 'Routine follow-up imaging per protocol'
          }
        }
        
      case 'outcome_bt_1b':
        return {
          ...step,
          status: 'completed',
          btradsScore: '1b',
          reasoning: 'BT-RADS 1b: Improvement likely due to medication effects (Avastin or steroids).',
          data: { 
            finalScore: 'BT-1b', 
            category: 'Medication Effect',
            clinicalAction: 'Consider medication effect vs. true tumor response',
            followUp: 'Close follow-up to assess sustained response'
          }
        }
        
      case 'outcome_bt_2':
        return {
          ...step,
          status: 'completed',
          btradsScore: '2',
          reasoning: 'BT-RADS 2: Stable. No significant change in tumor burden.',
          data: { 
            finalScore: 'BT-2', 
            category: 'Stable',
            clinicalAction: 'Continue current surveillance or treatment',
            followUp: 'Routine follow-up imaging per protocol'
          }
        }
        
      case 'outcome_bt_3a':
        return {
          ...step,
          status: 'completed',
          btradsScore: '3a',
          reasoning: 'BT-RADS 3a: Favor treatment effect. Changes likely related to recent radiation therapy.',
          data: { 
            finalScore: 'BT-3a', 
            category: 'Favor Treatment Effect',
            clinicalAction: 'Monitor for treatment-related changes',
            followUp: 'Short-term follow-up imaging in 1-3 months'
          }
        }
        
      case 'outcome_bt_3b':
        return {
          ...step,
          status: 'completed',
          btradsScore: '3b',
          reasoning: 'BT-RADS 3b: Indeterminate. Mixed pattern with single component progression.',
          data: { 
            finalScore: 'BT-3b', 
            category: 'Indeterminate',
            clinicalAction: 'Consider advanced imaging or biopsy',
            followUp: 'Short-term follow-up or tissue sampling'
          }
        }
        
      case 'outcome_bt_3c':
        return {
          ...step,
          status: 'completed',
          btradsScore: '3c',
          reasoning: 'BT-RADS 3c: Favor tumor progression. Non-progressive pattern but concerning changes.',
          data: { 
            finalScore: 'BT-3c', 
            category: 'Favor Tumor Progression',
            clinicalAction: 'Consider treatment change or biopsy',
            followUp: 'Close clinical follow-up, consider intervention'
          }
        }
        
      case 'outcome_bt_4':
        return {
          ...step,
          status: 'completed',
          btradsScore: '4',
          reasoning: 'BT-RADS 4: Highly suspicious for tumor progression. Significant increase or progressive pattern.',
          data: { 
            finalScore: 'BT-4', 
            category: 'Highly Suspicious',
            clinicalAction: 'Treatment change indicated',
            followUp: 'Immediate clinical action, treatment modification'
          }
        }
      
      default:
        return {
          ...step,
          status: 'completed',
          reasoning: 'Processing completed for this step.'
        }
    }
  }

  const toggleStepExpansion = (stepIndex: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(stepIndex)) {
        newSet.delete(stepIndex)
      } else {
        newSet.add(stepIndex)
      }
      return newSet
    })
  }

  const getStatusIcon = (status: ProcessingStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'processing':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      default:
        return <div className="h-5 w-5 rounded-full border-2 border-muted-foreground" />
    }
  }

  const getTypeIcon = (type: ProcessingStep['type']) => {
    switch (type) {
      case 'data-extraction':
        return <FileText className="h-4 w-4" />
      case 'decision':
        return <Activity className="h-4 w-4" />
      case 'outcome':
        return <Database className="h-4 w-4" />
      default:
        return <Stethoscope className="h-4 w-4" />
    }
  }

  if (!patientData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Clock className="h-8 w-8 animate-spin mx-auto mb-2 text-muted-foreground" />
          <p className="text-muted-foreground">Loading patient data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
        {/* Patient Header */}
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 border-blue-200 dark:border-blue-800">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-600" />
                Patient {patientData.data?.patient_id}
              </CardTitle>
              <div className="space-y-1">
                <CardDescription>
                  BT-RADS Decision Flow Analysis with Full Transparency
                </CardDescription>
                {extractionMode !== 'nlp' && (
                  <Badge variant="secondary">
                    {extractionMode === 'llm' ? 'LLM Extraction' : 'Dual Extraction'}
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Transparency Level Controls */}
              <div className="flex items-center gap-1 mr-4">
                <label className="text-xs font-medium text-muted-foreground">Detail Level:</label>
                <select
                  value={transparencyLevel}
                  onChange={(e) => setTransparencyLevel(e.target.value as any)}
                  className="text-xs border rounded px-2 py-1 bg-background"
                >
                  <option value="simple">Simple</option>
                  <option value="detailed">Detailed</option>
                  <option value="expert">Expert</option>
                  <option value="audit">Full Audit</option>
                </select>
              </div>
              {!isProcessing && currentStep === 0 && (
                <Button onClick={startProcessing} className="bg-blue-600 hover:bg-blue-700">
                  <Activity className="mr-2 h-4 w-4" />
                  Start Analysis
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        
        {/* Progress Indicator */}
        {(isProcessing || processingSteps.some(s => s.status !== 'pending')) && (
          <CardContent className="pt-0 pb-4">
            <div className="space-y-2">
              {(() => {
                // Check if processing is complete (reached an outcome node)
                const isComplete = processingSteps.some(s => 
                  s.type === 'outcome' && s.status === 'completed'
                )
                
                // Count steps that have been processed or are processing
                const activeSteps = processingSteps.filter(s => s.status !== 'pending')
                const completedSteps = activeSteps.filter(s => s.status === 'completed').length
                const totalActiveSteps = activeSteps.length
                
                // Progress calculation based on actual path
                let progressPercentage: number
                let progressText: string
                
                if (isComplete) {
                  progressPercentage = 100
                  progressText = `Processing Complete (${totalActiveSteps} steps)`
                } else if (totalActiveSteps === 0) {
                  progressPercentage = 0
                  progressText = 'Starting...'
                } else {
                  // Show progress based on completed steps out of active steps
                  progressPercentage = Math.max(5, Math.min(95, (completedSteps / (totalActiveSteps + 1)) * 100))
                  progressText = `Step ${completedSteps + 1} of ${totalActiveSteps + 1}`
                }
                
                return (
                  <>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Processing Progress</span>
                      <span className="font-medium">
                        {progressText}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-blue-600 transition-all duration-500 ease-out relative"
                        style={{
                          width: `${progressPercentage}%`
                        }}
                      >
                        {!isComplete && isProcessing && (
                          <div className="absolute inset-0 bg-white/20 animate-pulse" />
                        )}
                      </div>
                    </div>
                  </>
                )
              })()}
              {autoStart && !isProcessing && processingSteps.every(s => s.status === 'pending') && (
                <p className="text-xs text-muted-foreground text-center">
                  Auto-processing will begin shortly...
                </p>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Extraction Comparison View */}
      {extractionResults && Object.keys(extractionResults).length > 0 && (
        <ExtractionComparison 
          results={extractionResults} 
          extractionMode={extractionMode}
        />
      )}

      {/* Processing Steps */}
      <div className="space-y-1">
        {processingSteps.map((step, index) => {
          const isExpanded = expandedSteps.has(index)
          const isCurrentStep = index === currentStep
          const isVisible = step.status !== 'pending' || isCurrentStep || index === 0
          const isNextInPath = processingSteps.slice(0, index).some(s => s.nextNode === step.nodeId)
          
          if (!isVisible && !isNextInPath) return null

          const nextStepIndex = processingSteps.findIndex(s => s.nodeId === step.nextNode)
          const hasNextStep = nextStepIndex !== -1 && step.nextNode
          
          return (
            <div key={step.nodeId} className="relative">
              <Card className={`transition-all duration-500 ${
                isCurrentStep ? 'ring-2 ring-blue-500 shadow-lg scale-[1.02]' : 
                step.status === 'completed' ? 'border-green-200 bg-green-50/30 dark:bg-green-950/10' :
                step.status === 'processing' ? 'border-blue-200 bg-blue-50/30 dark:bg-blue-950/10 animate-pulse' :
                step.status === 'error' ? 'border-red-200 bg-red-50/30 dark:bg-red-950/10' :
                'border-muted opacity-60'
              }`}>
                <CardHeader 
                  className="cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => toggleStepExpansion(index)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(step.status)}
                        <Badge variant={
                          step.type === 'outcome' && step.btradsScore ? 
                            (step.btradsScore === '0' ? 'secondary' :
                             step.btradsScore.includes('1') ? 'default' :
                             step.btradsScore === '2' ? 'outline' : 'destructive') :
                            step.type === 'decision' ? 'secondary' : 'outline'
                        }>
                          {step.type.replace('-', ' ')}
                        </Badge>
                      </div>
                      <div>
                        <CardTitle className="text-base flex items-center gap-2">
                          {getTypeIcon(step.type)}
                          {step.label}
                          {step.nextNode && step.status === 'completed' && (
                            <>
                              <ArrowRight className="h-4 w-4 text-green-500" />
                              <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                                Next: {processingSteps.find(s => s.nodeId === step.nextNode)?.label || step.nextNode}
                              </Badge>
                            </>
                          )}
                        </CardTitle>
                        {step.btradsScore && step.status === 'completed' && (
                          <Badge 
                            variant={
                              step.btradsScore === '0' ? 'secondary' :
                              step.btradsScore.includes('1') ? 'default' :
                              step.btradsScore === '2' ? 'outline' : 'destructive'
                            } 
                            className="mt-1 font-semibold"
                          >
                            BT-RADS {step.btradsScore}
                          </Badge>
                        )}
                      </div>
                    </div>
                    {step.status === 'completed' && (
                      isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </CardHeader>
                
                {/* Main Results - Always Visible when completed */}
                {step.status === 'completed' && (
                  <>
                    <Separator />
                    <CardContent className="pt-4 space-y-4">
                      {/* Main Reasoning - Auto-displayed */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-sm text-foreground">Clinical Assessment:</h4>
                        </div>
                        <p className="text-sm text-foreground bg-gradient-to-r from-blue-50/50 to-indigo-50/50 dark:from-blue-950/20 dark:to-indigo-950/20 p-3 rounded-md leading-relaxed border border-blue-200/30 dark:border-blue-800/30">
                          {step.reasoning}
                        </p>
                      </div>

                      {/* Key Results - Auto-displayed */}
                      {step.data && (
                        <div>
                          {/* Special visual display for imaging assessment */}
                          {step.nodeId === 'node_2_imaging_assessment' && step.data ? (
                            <div className="space-y-3">
                              <div className="grid grid-cols-2 gap-3">
                                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 p-3 rounded-lg border border-blue-200 dark:border-blue-800">
                                  <div className="flex items-center gap-2 mb-2">
                                    <div className={`w-3 h-3 rounded-full ${
                                      step.data.flairChange < -10 ? 'bg-green-500' :
                                      step.data.flairChange > 10 ? 'bg-red-500' : 'bg-gray-400'
                                    }`} />
                                    <span className="font-medium text-sm">FLAIR Volume</span>
                                  </div>
                                  <p className="text-xs text-muted-foreground mb-1">{step.data.flairVolume}</p>
                                  <p className="text-lg font-bold">{typeof step.data.flairChange === 'number' ? step.data.flairChange.toFixed(1) : step.data.flairChange}%</p>
                                </div>
                                <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950/20 dark:to-pink-950/20 p-3 rounded-lg border border-purple-200 dark:border-purple-800">
                                  <div className="flex items-center gap-2 mb-2">
                                    <div className={`w-3 h-3 rounded-full ${
                                      step.data.enhChange < -10 ? 'bg-green-500' :
                                      step.data.enhChange > 10 ? 'bg-red-500' : 'bg-gray-400'
                                    }`} />
                                    <span className="font-medium text-sm">Enhancement Volume</span>
                                  </div>
                                  <p className="text-xs text-muted-foreground mb-1">{step.data.enhVolume}</p>
                                  <p className="text-lg font-bold">{typeof step.data.enhChange === 'number' ? step.data.enhChange.toFixed(1) : step.data.enhChange}%</p>
                                </div>
                              </div>
                              <div className="text-center p-3 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/20 dark:to-teal-950/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
                                <Badge variant="outline" className="text-base font-semibold px-4 py-1">
                                  Assessment: {step.data.assessment.toUpperCase()}
                                </Badge>
                              </div>
                            </div>
                          ) : (
                            /* Key results for other nodes */
                            <div className="space-y-2">
                              {/* Outcome nodes get special treatment */}
                              {step.type === 'outcome' ? (
                                <div className="text-center p-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20 rounded-lg border border-green-200 dark:border-green-800">
                                  <div className="space-y-2">
                                    <Badge variant="default" className="text-lg font-bold px-4 py-2">
                                      Final Score: BT-RADS {step.btradsScore}
                                    </Badge>
                                    <p className="text-sm font-medium text-green-700 dark:text-green-300">
                                      {step.data.category}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      {step.data.clinicalAction}
                                    </p>
                                  </div>
                                </div>
                              ) : (
                                /* Decision nodes show key factors */
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(step.data)
                                    .filter(([key, value]) => 
                                      !key.includes('Volume') && 
                                      !key.includes('Change') && 
                                      !key.includes('Absolute') &&
                                      typeof value !== 'object'
                                    )
                                    .slice(0, 3)
                                    .map(([key, value]) => (
                                      <Badge key={key} variant="outline" className="text-xs">
                                        {key.replace(/([A-Z])/g, ' $1').toLowerCase()}: {typeof value === 'number' ? value.toFixed(1) : String(value)}
                                      </Badge>
                                    ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Enhanced Transparency Components */}
                      {transparencyLevel !== 'simple' && (
                        <div className="space-y-4 mt-4">
                          {/* Evidence Highlighting */}
                          {step.evidence && step.evidence.length > 0 && (
                            <EvidenceHighlighter
                              text={patientData?.data?.clinical_note || ''}
                              evidence={step.evidence}
                              title="Clinical Note Evidence"
                              showControls={transparencyLevel === 'expert' || transparencyLevel === 'audit'}
                            />
                          )}
                          
                          {/* Calculation Breakdown */}
                          {step.calculations && step.calculations.length > 0 && (transparencyLevel !== 'simple') && (
                            <CalculationBreakdown
                              title="Volume Change Analysis"
                              calculations={step.calculations}
                              showFormulas={transparencyLevel === 'audit'}
                            />
                          )}
                          
                          {/* Confidence Indicator */}
                          {step.confidence && (transparencyLevel === 'detailed' || transparencyLevel === 'expert' || transparencyLevel === 'audit') && (
                            <ConfidenceIndicator
                              confidence={step.confidence}
                              compact={transparencyLevel === 'detailed'}
                              showDetails={transparencyLevel === 'expert' || transparencyLevel === 'audit'}
                            />
                          )}
                          
                          {/* Decision Audit Trail */}
                          {step.decisionPoint && (transparencyLevel === 'expert' || transparencyLevel === 'audit') && (
                            <DecisionAuditTrail
                              decisions={[step.decisionPoint]}
                              currentNodeId={step.nodeId}
                              showAlternatives={transparencyLevel === 'audit'}
                            />
                          )}
                          
                          {/* Manual Verification Panel */}
                          {step.verificationItems && transparencyLevel === 'audit' && (
                            <ManualVerificationPanel
                              items={step.verificationItems}
                              readonly={false}
                            />
                          )}
                        </div>
                      )}

                      {/* Expandable Advanced Details (Legacy) */}
                      {transparencyLevel === 'simple' && (step.data && Object.keys(step.data).length > 3) && (
                        <div className="border-t border-muted pt-3">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleStepExpansion(index + 1000) // Use different key to avoid conflict
                            }}
                            className="text-xs text-muted-foreground hover:text-foreground"
                          >
                            {expandedSteps.has(index + 1000) ? (
                              <>
                                <ChevronUp className="h-3 w-3 mr-1" />
                                Hide Details
                              </>
                            ) : (
                              <>
                                <ChevronDown className="h-3 w-3 mr-1" />
                                Show Advanced Details
                              </>
                            )}
                          </Button>
                          
                          {expandedSteps.has(index + 1000) && (
                            <div className="mt-3 p-3 bg-muted/10 rounded border">
                              <h5 className="font-medium text-xs mb-2 text-muted-foreground uppercase tracking-wide">
                                Detailed Analysis
                              </h5>
                              <div className="grid grid-cols-1 gap-2">
                                {Object.entries(step.data).map(([key, value]) => (
                                  <div key={key} className="flex justify-between items-center p-2 bg-background/50 rounded text-xs">
                                    <span className="font-medium text-muted-foreground">
                                      {key.replace(/([A-Z])/g, ' $1').toLowerCase().replace(/^./, str => str.toUpperCase())}:
                                    </span>
                                    <span className="font-mono text-foreground">
                                      {typeof value === 'object' ? JSON.stringify(value) : 
                                       typeof value === 'number' ? value.toFixed(1) : String(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </>
                )}
              </Card>
              
              {/* Enhanced Connection Line */}
              {hasNextStep && step.status === 'completed' && (
                <ConnectionLine
                  isActive={false}
                  isCompleted={true}
                  label={step.data?.assessment || step.data?.medicationPath || step.data?.timeCategory}
                />
              )}
              
              {isCurrentStep && step.status === 'processing' && (
                <ConnectionLine
                  isActive={true}
                  isCompleted={false}
                  label="Processing..."
                />
              )}
            </div>
          )
        })}
      </div>
      
      {/* Final Score Display */}
      {(() => {
        const finalStep = processingSteps.find(step => 
          step.type === 'outcome' && step.status === 'completed' && step.btradsScore
        )
        
        if (finalStep && finalStep.btradsScore) {
          const volumeData = {
            flairChange: parseFloat(patientData.data.flair_change_percentage || '0'),
            enhancementChange: parseFloat(patientData.data.enhancement_change_percentage || '0'),
            flairAbsolute: Math.abs((patientData.data.followup_flair_volume || 0) - (patientData.data.baseline_flair_volume || 0)),
            enhancementAbsolute: Math.abs((patientData.data.followup_enhancement_volume || 0) - (patientData.data.baseline_enhancement_volume || 0))
          }
          
          return (
            <div className="mt-8">
              <BTRADSFinalScore
                score={finalStep.btradsScore}
                steps={processingSteps}
                patientId={patientId}
                volumeData={volumeData}
                onGenerateReport={() => {
                  // TODO: Implement report generation
                  console.log('Generate report for:', patientId)
                }}
                onShareResults={() => {
                  // TODO: Implement share functionality
                  console.log('Share results for:', patientId)
                }}
                onProcessNext={onProcessNext}
                onProcessPrevious={onProcessPrevious}
                hasNextPatient={hasNextPatient}
                hasPreviousPatient={hasPreviousPatient}
                remainingCount={remainingCount}
                completedCount={completedCount}
                autoAdvance={autoAdvance}
                onAutoAdvanceChange={setAutoAdvance}
              />
            </div>
          )
        }
        
        return null
      })()}
    </div>
  )
}