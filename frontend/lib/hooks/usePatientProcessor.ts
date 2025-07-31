'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useBTRADSStore } from '@/lib/stores/btrads-store'
import { api } from '@/lib/api/client'
import { useWebSocket } from './useWebSocket'
import { Patient } from '@/types/patient'
import { AgentResult } from '@/types/agent'

export function usePatientProcessor(patientId: string) {
  const router = useRouter()
  const store = useBTRADSStore()
  
  const [patient, setPatient] = useState<Patient | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentNode, setCurrentNode] = useState<any>(null)
  const [validationPending, setValidationPending] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  
  const processingRef = useRef(false)
  
  // WebSocket connection
  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(
    `ws://localhost:8000/ws/${patientId}`
  )
  
  // Load patient data
  useEffect(() => {
    loadPatient()
  }, [patientId])
  
  const loadPatient = async () => {
    try {
      const data = await api.patients.get(patientId)
      setPatient(data)
      
      // Check if already processing
      const status = await api.patients.getStatus(patientId)
      setIsProcessing(status.is_processing)
      
      // Load any existing results
      if (data.completed) {
        const results = await api.agents.getResults(patientId)
        results.forEach((result: AgentResult) => {
          store.setAgentResult(result.node_id, result)
          store.setNodeStatus(result.node_id, 'completed')
        })
      }
    } catch (err) {
      setError('Failed to load patient data')
      console.error(err)
    }
  }
  
  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return
    
    const data = JSON.parse(lastMessage)
    
    switch (data.type) {
      case 'node_activated':
        store.setActiveNode(data.node_id)
        store.addToPath(data.node_id)
        setCurrentNode(data)
        break
        
      case 'extraction_complete':
        store.setAgentResult(data.node_id, data.data)
        if (data.requires_validation) {
          store.setNodeStatus(data.node_id, 'needs-validation')
          setValidationPending(data.data)
        } else {
          store.setNodeStatus(data.node_id, 'completed')
        }
        break
        
      case 'validation_required':
        setValidationPending(data.agent_result)
        break
        
      case 'completed':
        setIsProcessing(false)
        processingRef.current = false
        store.setActiveNode(null)
        loadPatient() // Reload to get final results
        break
        
      case 'error':
        setError(data.error)
        setIsProcessing(false)
        processingRef.current = false
        break
    }
  }, [lastMessage, store])
  
  // Start processing
  const startProcessing = useCallback(async (autoValidate = false) => {
    if (processingRef.current) return
    
    try {
      processingRef.current = true
      setIsProcessing(true)
      setError(null)
      store.resetState()
      
      await api.patients.startProcessing(patientId, autoValidate)
    } catch (err) {
      setError('Failed to start processing')
      setIsProcessing(false)
      processingRef.current = false
      console.error(err)
    }
  }, [patientId, store])
  
  // Pause processing
  const pauseProcessing = useCallback(() => {
    // In a real implementation, would send pause command
    setIsProcessing(false)
    processingRef.current = false
  }, [])
  
  // Validate result
  const validateResult = useCallback(async (
    validationId: string,
    value: any,
    notes?: string
  ) => {
    try {
      await api.validation.validate({
        patient_id: patientId,
        validation_id: validationId,
        validated_value: value,
        notes,
        validator_id: 'current-user' // Would come from auth
      })
      
      setValidationPending(null)
    } catch (err) {
      setError('Failed to validate result')
      console.error(err)
    }
  }, [patientId])
  
  // Export results
  const exportResults = useCallback(async () => {
    try {
      const blob = await api.reports.exportPDF(patientId)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `btrads_report_${patientId}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      setError('Failed to export results')
      console.error(err)
    }
  }, [patientId])
  
  return {
    patient,
    isProcessing,
    currentNode,
    validationPending,
    error,
    connectionStatus,
    startProcessing,
    pauseProcessing,
    validateResult,
    exportResults,
    reload: loadPatient
  }
}