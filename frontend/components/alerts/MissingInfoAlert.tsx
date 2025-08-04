'use client'

import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  AlertTriangle, 
  Info, 
  CheckCircle, 
  XCircle,
  Calendar,
  Pill,
  Brain,
  Database,
  HelpCircle
} from "lucide-react"
import type { 
  MissingInfoItem, 
  UserProvidedData, 
  FallbackOption,
  DataValidation 
} from '@/types/missing-info'

interface MissingInfoAlertProps {
  item: MissingInfoItem
  isOpen: boolean
  onResolve: (data: UserProvidedData) => void
  onSkip?: () => void
  previousValue?: UserProvidedData
}

export function MissingInfoAlert({ 
  item, 
  isOpen, 
  onResolve, 
  onSkip,
  previousValue 
}: MissingInfoAlertProps) {
  const [inputValue, setInputValue] = useState(previousValue?.providedValue || '')
  const [selectedFallback, setSelectedFallback] = useState(
    previousValue?.selectedFallback || item.defaultFallback || ''
  )
  const [notes, setNotes] = useState(previousValue?.notes || '')
  const [validation, setValidation] = useState<DataValidation>({ isValid: true })
  const [inputMode, setInputMode] = useState<'manual' | 'fallback'>(
    previousValue?.providedValue ? 'manual' : 'fallback'
  )

  const getIcon = () => {
    switch (item.type) {
      case 'medication_status':
        return <Pill className="h-5 w-5" />
      case 'radiation_date':
        return <Calendar className="h-5 w-5" />
      case 'volume_data':
        return <Database className="h-5 w-5" />
      case 'clinical_assessment':
        return <Brain className="h-5 w-5" />
      default:
        return <AlertTriangle className="h-5 w-5" />
    }
  }

  const getSeverityColor = () => {
    switch (item.severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'important':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'optional':
        return 'text-blue-600 bg-blue-50 border-blue-200'
    }
  }

  const validateInput = (value: any): DataValidation => {
    const errors: string[] = []
    const warnings: string[] = []
    
    if (!item.validationRules) {
      return { isValid: true }
    }

    const { type, min, max, pattern, required } = item.validationRules

    if (required && !value) {
      errors.push('This field is required')
    }

    if (value && type) {
      switch (type) {
        case 'date':
          const dateRegex = /^\d{1,2}\/\d{1,2}\/\d{2,4}$/
          if (!dateRegex.test(value)) {
            errors.push('Please enter a valid date (MM/DD/YYYY)')
          }
          break
        case 'number':
          const numValue = parseFloat(value)
          if (isNaN(numValue)) {
            errors.push('Please enter a valid number')
          } else {
            if (min !== undefined && numValue < min) {
              errors.push(`Value must be at least ${min}`)
            }
            if (max !== undefined && numValue > max) {
              errors.push(`Value must be at most ${max}`)
            }
          }
          break
        case 'text':
          if (pattern) {
            const regex = new RegExp(pattern)
            if (!regex.test(value)) {
              errors.push('Invalid format')
            }
          }
          break
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    }
  }

  const handleInputChange = (value: string) => {
    setInputValue(value)
    const validationResult = validateInput(value)
    setValidation(validationResult)
  }

  const handleResolve = () => {
    if (inputMode === 'manual' && !validation.isValid) {
      return
    }

    const resolvedValue = inputMode === 'manual' 
      ? inputValue 
      : item.fallbackOptions?.find(opt => opt.id === selectedFallback)?.value

    const data: UserProvidedData = {
      itemId: item.id,
      providedValue: resolvedValue,
      selectedFallback: inputMode === 'fallback' ? selectedFallback : undefined,
      confirmedMissing: inputMode === 'fallback',
      notes,
      timestamp: new Date(),
      provider: 'user'
    }

    onResolve(data)
  }

  const renderInputField = () => {
    switch (item.type) {
      case 'medication_status':
        return (
          <div className="space-y-3">
            <div>
              <Label htmlFor="steroid-status">Steroid Status</Label>
              <RadioGroup 
                id="steroid-status"
                value={inputValue.steroidStatus || ''} 
                onValueChange={(value) => 
                  handleInputChange({ ...inputValue, steroidStatus: value })
                }
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="none" id="steroid-none" />
                  <Label htmlFor="steroid-none">No steroids</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="stable" id="steroid-stable" />
                  <Label htmlFor="steroid-stable">Stable dose</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="increasing" id="steroid-increasing" />
                  <Label htmlFor="steroid-increasing">Increasing dose</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="decreasing" id="steroid-decreasing" />
                  <Label htmlFor="steroid-decreasing">Decreasing/Tapering</Label>
                </div>
              </RadioGroup>
            </div>
            <div>
              <Label htmlFor="avastin-status">Avastin Status</Label>
              <RadioGroup 
                id="avastin-status"
                value={inputValue.avastinStatus || ''} 
                onValueChange={(value) => 
                  handleInputChange({ ...inputValue, avastinStatus: value })
                }
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="none" id="avastin-none" />
                  <Label htmlFor="avastin-none">No Avastin</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="first_treatment" id="avastin-first" />
                  <Label htmlFor="avastin-first">First treatment/study</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="ongoing" id="avastin-ongoing" />
                  <Label htmlFor="avastin-ongoing">Ongoing treatment</Label>
                </div>
              </RadioGroup>
            </div>
          </div>
        )
      
      case 'radiation_date':
        return (
          <div className="space-y-2">
            <Label htmlFor="radiation-date">Radiation Completion Date</Label>
            <Input
              id="radiation-date"
              type="text"
              placeholder="MM/DD/YYYY"
              value={inputValue}
              onChange={(e) => handleInputChange(e.target.value)}
              className={validation.errors?.length ? 'border-red-500' : ''}
            />
            {validation.errors?.map((error, idx) => (
              <p key={idx} className="text-sm text-red-600">{error}</p>
            ))}
            <p className="text-xs text-muted-foreground">
              Enter the date when radiation therapy was completed
            </p>
          </div>
        )
      
      case 'volume_data':
        return (
          <div className="space-y-2">
            <Label htmlFor="volume">Volume (mL)</Label>
            <Input
              id="volume"
              type="number"
              step="0.1"
              placeholder="Enter volume in mL"
              value={inputValue}
              onChange={(e) => handleInputChange(e.target.value)}
              className={validation.errors?.length ? 'border-red-500' : ''}
            />
            {validation.errors?.map((error, idx) => (
              <p key={idx} className="text-sm text-red-600">{error}</p>
            ))}
          </div>
        )
      
      default:
        return (
          <div className="space-y-2">
            <Label htmlFor="manual-input">Enter Value</Label>
            <Input
              id="manual-input"
              type="text"
              value={inputValue}
              onChange={(e) => handleInputChange(e.target.value)}
              className={validation.errors?.length ? 'border-red-500' : ''}
            />
            {validation.errors?.map((error, idx) => (
              <p key={idx} className="text-sm text-red-600">{error}</p>
            ))}
          </div>
        )
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getIcon()}
            Missing Information: {item.label}
          </DialogTitle>
          <DialogDescription>
            {item.description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Severity and Context */}
          <Alert className={`border ${getSeverityColor()}`}>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-1">
                <p className="font-medium">
                  This information is {item.severity} for:
                </p>
                <ul className="list-disc list-inside text-sm">
                  {item.requiredFor.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            </AlertDescription>
          </Alert>

          {/* Current extraction info */}
          {item.confidence !== undefined && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Extraction confidence: {item.confidence}%
              </span>
              <Badge variant={item.confidence > 70 ? 'default' : 'secondary'}>
                {item.extractionMethod || 'unknown'} extraction
              </Badge>
            </div>
          )}

          <Separator />

          {/* Input Mode Selection */}
          <div className="space-y-3">
            <Label>How would you like to provide this information?</Label>
            <RadioGroup value={inputMode} onValueChange={(value: 'manual' | 'fallback') => setInputMode(value)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="manual" id="input-manual" />
                <Label htmlFor="input-manual" className="cursor-pointer">
                  Enter value manually
                </Label>
              </div>
              {item.fallbackOptions && item.fallbackOptions.length > 0 && (
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="fallback" id="input-fallback" />
                  <Label htmlFor="input-fallback" className="cursor-pointer">
                    Use a fallback option
                  </Label>
                </div>
              )}
            </RadioGroup>
          </div>

          {/* Manual Input */}
          {inputMode === 'manual' && (
            <div className="space-y-3">
              {renderInputField()}
            </div>
          )}

          {/* Fallback Options */}
          {inputMode === 'fallback' && item.fallbackOptions && (
            <div className="space-y-3">
              <Label>Select a fallback option:</Label>
              <RadioGroup value={selectedFallback} onValueChange={setSelectedFallback}>
                {item.fallbackOptions.map((option) => (
                  <div key={option.id} className="space-y-2">
                    <div className="flex items-start space-x-2">
                      <RadioGroupItem value={option.id} id={option.id} className="mt-1" />
                      <div className="flex-1">
                        <Label htmlFor={option.id} className="cursor-pointer">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span>{option.label}</span>
                              {option.isConservative && (
                                <Badge variant="outline" className="text-xs">
                                  Conservative
                                </Badge>
                              )}
                            </div>
                            {option.description && (
                              <p className="text-sm text-muted-foreground font-normal">
                                {option.description}
                              </p>
                            )}
                            {option.consequences && (
                              <p className="text-xs text-yellow-600 font-normal">
                                ⚠️ {option.consequences}
                              </p>
                            )}
                          </div>
                        </Label>
                      </div>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes (optional)</Label>
            <Textarea
              id="notes"
              placeholder="Add any relevant context or explanation..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          {onSkip && (
            <Button
              variant="ghost"
              onClick={onSkip}
            >
              Skip for now
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => {
              const data: UserProvidedData = {
                itemId: item.id,
                providedValue: null,
                confirmedMissing: true,
                notes: 'User confirmed data is unavailable',
                timestamp: new Date(),
                provider: 'user'
              }
              onResolve(data)
            }}
          >
            Confirm Missing
          </Button>
          <Button
            onClick={handleResolve}
            disabled={
              inputMode === 'manual' ? !validation.isValid || !inputValue : 
              inputMode === 'fallback' ? !selectedFallback : false
            }
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            Resolve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}