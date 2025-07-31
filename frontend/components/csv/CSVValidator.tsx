'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  FileSpreadsheet,
  ArrowRight,
  Loader2,
  Database,
  Settings,
  ChevronDown,
  ChevronUp,
  FileText,
  Hash,
  Calendar
} from "lucide-react"
import { Separator } from "@/components/ui/separator"

interface ColumnMapping {
  csvColumn: string
  btradsField: string
  status: 'valid' | 'missing' | 'optional'
  example?: string
}

interface ValidationResult {
  isValid: boolean
  mappings: ColumnMapping[]
  errors: string[]
  warnings: string[]
  totalRows: number
  validRows: number
}

interface CSVValidatorProps {
  csvData: any[]
  onValidationComplete: (result: ValidationResult) => void
  isUploading?: boolean
}

export function CSVValidator({ csvData, onValidationComplete, isUploading = false }: CSVValidatorProps) {
  const [validationSteps, setValidationSteps] = useState([
    { id: 1, name: 'Column Mapping', status: 'pending', description: 'Mapping CSV columns to BT-RADS fields' },
    { id: 2, name: 'Data Validation', status: 'pending', description: 'Validating data types and formats' },
    { id: 3, name: 'Completeness Check', status: 'pending', description: 'Checking for required fields' },
    { id: 4, name: 'Summary', status: 'pending', description: 'Final validation report' }
  ])
  
  const [currentStep, setCurrentStep] = useState(0)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [hasStartedValidation, setHasStartedValidation] = useState(false)

  const requiredFieldMappings = {
    'patient_id': ['patient_id', 'id', 'Patient ID', 'PatientID', 'patient id', 'patient_id', 'ID', 'Patient_ID', 'pid', 'PID'],
    'clinical_note': ['clinical_note', 'Clinical Note', 'note', 'Notes', 'clinical_notes', 'Clinical_Note', 'clinical note', 'clinical_note_closest', 'Clinical_Note_Closest'],
    'baseline_date': ['baseline_date', 'Baseline_imaging_date', 'BaselineDate', 'baseline date', 'Baseline Date', 'Baseline_Date'],
    'followup_date': ['followup_date', 'Followup_imaging_date', 'FollowupDate', 'followup date', 'Followup Date', 'Followup_Date', 'follow_up_date']
  }

  const optionalFieldMappings = {
    'baseline_flair_volume': ['baseline_flair_volume', 'Baseline_flair_volume', 'baseline flair volume', 'Baseline FLAIR Volume', 'Baseline_FLAIR_Volume'],
    'followup_flair_volume': ['followup_flair_volume', 'Followup_flair_volume', 'followup flair volume', 'Followup FLAIR Volume', 'Followup_FLAIR_Volume'],
    'flair_change_percentage': ['flair_change_percentage', 'Volume_Difference_flair_Percentage_Change', 'FLAIR Change %', 'flair change percentage', 'FLAIR_Change_Percentage'],
    'baseline_enhancement_volume': ['baseline_enhancement_volume', 'Baseline_enhancement_volume', 'baseline enhancement volume', 'Baseline Enhancement Volume', 'Baseline_Enhancement_Volume'],
    'followup_enhancement_volume': ['followup_enhancement_volume', 'Followup_enhancement_volume', 'followup enhancement volume', 'Followup Enhancement Volume', 'Followup_Enhancement_Volume'],
    'enhancement_change_percentage': ['enhancement_change_percentage', 'Volume_Difference_enhancement_Percentage_Change', 'Enhancement Change %', 'enhancement change percentage', 'Enhancement_Change_Percentage'],
    'ground_truth_btrads': ['ground_truth_btrads', 'BTRADS (Precise Category)', 'BT-RADS', 'ground truth btrads', 'Ground Truth BT-RADS', 'Ground_Truth_BTRADS', 'Ground_Truth_BTRADS (Precise Category)', 'Ground_Truth_BTRADS (General Category)']
  }

  const validateCSV = useCallback(async () => {
    setIsValidating(true)
    const csvColumns = csvData.length > 0 ? Object.keys(csvData[0]) : []
    const mappings: ColumnMapping[] = []
    const errors: string[] = []
    const warnings: string[] = []

    // Add info about found columns
    if (csvColumns.length > 0) {
      console.log('CSV columns found:', csvColumns)
    }

    // Step 1: Column Mapping
    updateStepStatus(1, 'active')

    // Check required fields
    for (const [field, possibleNames] of Object.entries(requiredFieldMappings)) {
      const foundColumn = csvColumns.find(col => 
        possibleNames.some(name => col.toLowerCase().trim() === name.toLowerCase().trim())
      )
      
      if (foundColumn) {
        mappings.push({
          csvColumn: foundColumn,
          btradsField: field,
          status: 'valid',
          example: csvData[0][foundColumn]
        })
      } else {
        mappings.push({
          csvColumn: '---',
          btradsField: field,
          status: 'missing'
        })
        errors.push(`Required field "${field}" not found in CSV. Looked for columns: ${possibleNames.join(', ')}`)
      }
    }

    // Check optional fields
    for (const [field, possibleNames] of Object.entries(optionalFieldMappings)) {
      const foundColumn = csvColumns.find(col => 
        possibleNames.some(name => col.toLowerCase().trim() === name.toLowerCase().trim())
      )
      
      if (foundColumn) {
        mappings.push({
          csvColumn: foundColumn,
          btradsField: field,
          status: 'valid',
          example: csvData[0][foundColumn]
        })
      } else {
        mappings.push({
          csvColumn: '---',
          btradsField: field,
          status: 'optional'
        })
        warnings.push(`Optional field "${field}" not found. Looked for columns: ${possibleNames.join(', ')}`)
      }
    }

    updateStepStatus(1, 'completed')

    // Step 2: Data Validation
    updateStepStatus(2, 'active')

    let validRows = 0
    csvData.forEach((row, index) => {
      let rowValid = true
      
      // Validate dates
      const dateFields = ['baseline_date', 'followup_date']
      dateFields.forEach(field => {
        const mapping = mappings.find(m => m.btradsField === field && m.status === 'valid')
        if (mapping && row[mapping.csvColumn]) {
          const dateValue = row[mapping.csvColumn]
          
          // Try multiple date formats
          const validDate = isValidDate(dateValue)
          if (!validDate) {
            errors.push(`Row ${index + 1}: Invalid date format for ${field}. Value: "${dateValue}". Expected formats: YYYY-MM-DD, MM/DD/YYYY, MM-DD-YYYY`)
            rowValid = false
          }
        }
      })

      // Validate numeric fields
      const numericFields = [
        'baseline_flair_volume', 'followup_flair_volume', 'flair_change_percentage',
        'baseline_enhancement_volume', 'followup_enhancement_volume', 'enhancement_change_percentage'
      ]
      numericFields.forEach(field => {
        const mapping = mappings.find(m => m.btradsField === field && m.status === 'valid')
        if (mapping && row[mapping.csvColumn]) {
          const value = parseFloat(row[mapping.csvColumn])
          if (isNaN(value)) {
            warnings.push(`Row ${index + 1}: Invalid numeric value for ${field}`)
          }
        }
      })

      if (rowValid) validRows++
    })

    updateStepStatus(2, 'completed')

    // Step 3: Completeness Check
    updateStepStatus(3, 'active')

    const requiredFieldsPresent = mappings.filter(m => 
      Object.keys(requiredFieldMappings).includes(m.btradsField) && m.status === 'valid'
    ).length

    const completenessPercentage = (requiredFieldsPresent / Object.keys(requiredFieldMappings).length) * 100

    if (completenessPercentage < 100) {
      errors.push(`Only ${completenessPercentage}% of required fields are present`)
    }

    updateStepStatus(3, 'completed')

    // Step 4: Summary
    updateStepStatus(4, 'active')

    const result: ValidationResult = {
      isValid: errors.length === 0,
      mappings,
      errors,
      warnings,
      totalRows: csvData.length,
      validRows
    }

    setValidationResult(result)
    updateStepStatus(4, 'completed')
    setIsValidating(false)
    setExpandedSection('summary')
    
    // Don't auto-upload, let user click the button
    // onValidationComplete(result)
  }, [csvData, onValidationComplete])

  // Auto-start validation when component mounts
  useEffect(() => {
    if (csvData.length > 0 && !hasStartedValidation && !validationResult) {
      setHasStartedValidation(true)
      validateCSV()
    }
  }, [csvData, hasStartedValidation, validationResult, validateCSV])

  const updateStepStatus = (stepId: number, status: 'pending' | 'active' | 'completed') => {
    setValidationSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, status } : step
    ))
    if (status === 'active') {
      setCurrentStep(stepId - 1)
    } else if (status === 'completed' && stepId === validationSteps.length) {
      // When last step completes, set progress to 100%
      setCurrentStep(validationSteps.length)
    }
  }

  // Removed simulateDelay - validation should be instant

  const isValidDate = (dateString: string): boolean => {
    if (!dateString) return false
    
    // Try multiple date formats
    const formats = [
      // ISO format
      /^\d{4}-\d{2}-\d{2}$/,
      // US format
      /^\d{1,2}\/\d{1,2}\/\d{4}$/,
      // Alternative format
      /^\d{1,2}-\d{1,2}-\d{4}$/,
    ]
    
    // Check if matches any format
    const matchesFormat = formats.some(format => format.test(dateString.trim()))
    if (!matchesFormat) return false
    
    // Try to parse the date
    const date = new Date(dateString)
    return !isNaN(date.getTime()) && date.getFullYear() > 1900 && date.getFullYear() < 2100
  }

  const getFieldIcon = (field: string) => {
    if (field.includes('id')) return <Hash className="h-3 w-3" />
    if (field.includes('date')) return <Calendar className="h-3 w-3" />
    if (field.includes('note')) return <FileText className="h-3 w-3" />
    return <Database className="h-3 w-3" />
  }

  return (
    <div className="space-y-6">
      {/* Validation Progress */}
      <Card className="shadow-soft">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Settings className="h-5 w-5" />
            CSV Validation Process
          </CardTitle>
          <CardDescription>
            Analyzing your CSV file structure and data integrity
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Progress value={(currentStep / validationSteps.length) * 100} className="h-2" />
          
          <div className="space-y-3">
            {validationSteps.map((step) => (
              <div key={step.id} className="flex items-center gap-4">
                <div className="flex-shrink-0">
                  {step.status === 'completed' ? (
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  ) : step.status === 'active' ? (
                    <Loader2 className="h-5 w-5 text-primary animate-spin" />
                  ) : (
                    <div className="h-5 w-5 rounded-full border-2 border-muted" />
                  )}
                </div>
                <div className="flex-1">
                  <p className={cn(
                    "font-medium text-sm",
                    step.status === 'active' && 'text-primary',
                    step.status === 'completed' && 'text-success',
                    step.status === 'pending' && 'text-muted-foreground'
                  )}>
                    {step.name}
                  </p>
                  <p className="text-xs text-muted-foreground">{step.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Auto-validation starts automatically - no button needed */}
        </CardContent>
      </Card>

      {/* CSV info is shown in validation results */}

      {/* Validation Results */}
      {validationResult && (
        <div className="space-y-4">
          {/* Summary Card */}
          <Card className={`shadow-soft ${validationResult.isValid ? 'border-success/20' : 'border-warning/20'}`}>
            <CardHeader 
              className="cursor-pointer"
              onClick={() => setExpandedSection(expandedSection === 'summary' ? null : 'summary')}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {validationResult.isValid ? (
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-warning" />
                  )}
                  <CardTitle className="text-lg">
                    {validationResult.isValid ? 'Validation Successful' : 'Validation Issues Found'}
                  </CardTitle>
                </div>
                {expandedSection === 'summary' ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            
            {expandedSection === 'summary' && (
              <>
                <Separator />
                <CardContent className="space-y-4 pt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm font-medium">Total Rows</p>
                      <p className="text-2xl font-bold">{validationResult.totalRows}</p>
                    </div>
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm font-medium">Valid Rows</p>
                      <p className="text-2xl font-bold text-success">{validationResult.validRows}</p>
                    </div>
                  </div>

                  {validationResult.errors.length > 0 && (
                    <Alert variant="destructive" className="border-destructive/20">
                      <XCircle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Errors ({validationResult.errors.length}):</strong>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                          {validationResult.errors.slice(0, 3).map((error, index) => (
                            <li key={index} className="text-sm">{error}</li>
                          ))}
                          {validationResult.errors.length > 3 && (
                            <li className="text-sm text-muted-foreground">
                              ... and {validationResult.errors.length - 3} more
                            </li>
                          )}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}

                  {validationResult.warnings.length > 0 && (
                    <Alert className="border-warning/20">
                      <AlertCircle className="h-4 w-4 text-warning" />
                      <AlertDescription>
                        <strong>Warnings ({validationResult.warnings.length}):</strong>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                          {validationResult.warnings.slice(0, 3).map((warning, index) => (
                            <li key={index} className="text-sm">{warning}</li>
                          ))}
                          {validationResult.warnings.length > 3 && (
                            <li className="text-sm text-muted-foreground">
                              ... and {validationResult.warnings.length - 3} more
                            </li>
                          )}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}

                  {validationResult.isValid && (
                    <Button 
                      onClick={() => onValidationComplete(validationResult)}
                      className="w-full" 
                      size="lg"
                      disabled={isUploading}
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Uploading {validationResult.validRows} Patients...
                        </>
                      ) : (
                        <>
                          <ArrowRight className="mr-2 h-4 w-4" />
                          Upload {validationResult.validRows} Patients to Server
                        </>
                      )}
                    </Button>
                  )}
                </CardContent>
              </>
            )}
          </Card>

          {/* Column Mappings Card */}
          <Card className="shadow-soft">
            <CardHeader 
              className="cursor-pointer"
              onClick={() => setExpandedSection(expandedSection === 'mappings' ? null : 'mappings')}
            >
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileSpreadsheet className="h-5 w-5" />
                  Column Mappings
                </CardTitle>
                {expandedSection === 'mappings' ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            
            {expandedSection === 'mappings' && (
              <>
                <Separator />
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    {validationResult.mappings.map((mapping, index) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                        <div className="flex items-center gap-3">
                          {getFieldIcon(mapping.btradsField)}
                          <div>
                            <p className="text-sm font-medium">{mapping.btradsField}</p>
                            {mapping.example && (
                              <p className="text-xs text-muted-foreground">
                                Example: {mapping.example.toString().substring(0, 30)}...
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-muted-foreground">
                            {mapping.csvColumn}
                          </span>
                          <Badge 
                            variant={
                              mapping.status === 'valid' ? 'default' : 
                              mapping.status === 'missing' ? 'destructive' : 
                              'secondary'
                            }
                            className="text-xs"
                          >
                            {mapping.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}