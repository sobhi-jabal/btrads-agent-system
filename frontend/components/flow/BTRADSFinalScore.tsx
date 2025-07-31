'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
import { 
  AlertCircle, 
  Info, 
  Clock,
  FileText,
  Download,
  Share2,
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  ChevronLeft,
  ListChecks,
  Timer
} from "lucide-react"
import type { ProcessingStep } from './BTRADSDecisionFlow'

interface BTRADSFinalScoreProps {
  score: string
  steps: ProcessingStep[]
  patientId: string
  volumeData?: {
    flairChange: number
    enhancementChange: number
    flairAbsolute: number
    enhancementAbsolute: number
  }
  onGenerateReport?: () => void
  onShareResults?: () => void
  onProcessNext?: () => void
  onProcessPrevious?: () => void
  hasNextPatient?: boolean
  hasPreviousPatient?: boolean
  remainingCount?: number
  completedCount?: number
  autoAdvance?: boolean
  onAutoAdvanceChange?: (enabled: boolean) => void
}

const scoreDescriptions: Record<string, { 
  label: string
  description: string
  color: string
  icon: React.ReactNode
}> = {
  '0': {
    label: 'BT-RADS 0 - Incomplete',
    description: 'Incomplete assessment due to lack of suitable prior comparison',
    color: 'secondary',
    icon: <Info className="h-5 w-5" />
  },
  '1a': {
    label: 'BT-RADS 1a - Improved',
    description: 'True improvement in tumor burden, not explained by medication effects',
    color: 'success',
    icon: <TrendingDown className="h-5 w-5 text-green-600" />
  },
  '1b': {
    label: 'BT-RADS 1b - Improved (Medication Effect)',
    description: 'Improvement likely due to anti-angiogenic therapy or steroid effects',
    color: 'warning',
    icon: <TrendingDown className="h-5 w-5 text-yellow-600" />
  },
  '2': {
    label: 'BT-RADS 2 - Stable',
    description: 'No significant change in tumor burden',
    color: 'default',
    icon: <Minus className="h-5 w-5" />
  },
  '3a': {
    label: 'BT-RADS 3a - Progression (Radiation Effect)',
    description: 'Worsening within expected radiation treatment timeframe (<90 days)',
    color: 'destructive',
    icon: <Clock className="h-5 w-5 text-orange-600" />
  },
  '3b': {
    label: 'BT-RADS 3b - Progression (FLAIR-Predominant)',
    description: 'FLAIR-predominant progression pattern',
    color: 'destructive',
    icon: <AlertCircle className="h-5 w-5 text-orange-600" />
  },
  '3c': {
    label: 'BT-RADS 3c - Progression (Equivocal)',
    description: 'Equivocal findings for progression',
    color: 'destructive',
    icon: <AlertCircle className="h-5 w-5 text-red-600" />
  },
  '4': {
    label: 'BT-RADS 4 - Definite Progression',
    description: 'Definite tumor progression with clear progressive pattern',
    color: 'destructive',
    icon: <TrendingUp className="h-5 w-5 text-red-600" />
  }
}

export function BTRADSFinalScore({ 
  score, 
  steps, 
  patientId,
  volumeData,
  onGenerateReport,
  onShareResults,
  onProcessNext,
  onProcessPrevious,
  hasNextPatient = false,
  hasPreviousPatient = false,
  remainingCount = 0,
  completedCount = 0,
  autoAdvance = false,
  onAutoAdvanceChange
}: BTRADSFinalScoreProps) {
  const scoreInfo = scoreDescriptions[score] || scoreDescriptions['0']
  const [countdown, setCountdown] = useState<number | null>(null)
  
  // Extract key decision points from steps
  const keyDecisions = steps.filter(step => 
    step.type === 'decision' && step.status === 'completed'
  )
  
  // Get the final outcome step
  const outcomeStep = steps.find(step => 
    step.type === 'outcome' && step.status === 'completed'
  )

  // Auto-advance countdown
  useEffect(() => {
    if (autoAdvance && hasNextPatient && onProcessNext) {
      setCountdown(3)
      const timer = setInterval(() => {
        setCountdown(prev => {
          if (prev === null || prev <= 1) {
            clearInterval(timer)
            onProcessNext()
            return null
          }
          return prev - 1
        })
      }, 1000)
      
      return () => clearInterval(timer)
    } else {
      setCountdown(null)
    }
  }, [autoAdvance, hasNextPatient, onProcessNext])

  const getVolumeIcon = (change: number) => {
    if (change < -10) return <TrendingDown className="h-4 w-4 text-green-600" />
    if (change > 10) return <TrendingUp className="h-4 w-4 text-red-600" />
    return <Minus className="h-4 w-4 text-gray-600" />
  }

  return (
    <Card className="w-full border-2 border-primary/20 shadow-lg">
      <CardHeader className="bg-gradient-to-r from-primary/5 to-primary/10">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <CardTitle className="text-2xl flex items-center gap-3">
              <Brain className="h-8 w-8 text-primary" />
              Final BT-RADS Assessment
            </CardTitle>
            <CardDescription>
              Patient ID: {patientId} | Processed: {new Date().toLocaleString()}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {onGenerateReport && (
              <Button variant="outline" size="sm" onClick={onGenerateReport}>
                <FileText className="h-4 w-4 mr-2" />
                Generate Report
              </Button>
            )}
            {onShareResults && (
              <Button variant="outline" size="sm" onClick={onShareResults}>
                <Share2 className="h-4 w-4 mr-2" />
                Share
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-6">
        {/* Main Score Display */}
        <div className="text-center space-y-4 p-6 bg-gradient-to-r from-primary/5 to-primary/10 rounded-lg">
          <div className="flex items-center justify-center gap-3">
            {scoreInfo.icon}
            <h2 className="text-3xl font-bold">{scoreInfo.label}</h2>
          </div>
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            {scoreInfo.description}
          </p>

          {volumeData && (
            <div className="flex items-center justify-center gap-6 mt-4">
              <Badge variant="outline" className="text-base px-3 py-1">
                FLAIR: {volumeData.flairChange.toFixed(1)}%
                {getVolumeIcon(volumeData.flairChange)}
              </Badge>
              <Badge variant="outline" className="text-base px-3 py-1">
                Enhancement: {volumeData.enhancementChange.toFixed(1)}%
                {getVolumeIcon(volumeData.enhancementChange)}
              </Badge>
            </div>
          )}
        </div>

        <Separator />

        {/* Decision Summary */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Key Decision Points</h3>
          <div className="space-y-2">
            {keyDecisions.map((decision, index) => (
              <Card key={decision.nodeId} className="border-l-4 border-l-primary">
                <CardContent className="py-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <p className="font-medium">{index + 1}. {decision.label}</p>
                      <p className="text-sm text-muted-foreground">
                        {decision.reasoning || decision.decisionPoint?.selectedPath}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Processing Path */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Processing Path</h3>
          <div className="flex flex-wrap gap-2">
            {steps
              .filter(s => s.status === 'completed')
              .map((step, index) => (
                <Badge 
                  key={step.nodeId} 
                  variant={step.type === 'outcome' ? 'default' : 'outline'}
                  className="text-xs"
                >
                  {index + 1}. {step.label}
                </Badge>
              ))}
          </div>
        </div>

        {/* Additional Notes */}
        {outcomeStep?.reasoning && (
          <>
            <Separator />
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Clinical Context</h3>
              <Card className="border-muted">
                <CardContent className="pt-4">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {outcomeStep.reasoning}
                  </p>
                </CardContent>
              </Card>
            </div>
          </>
        )}

        {/* Export Options */}
        <Separator />
        <div className="flex justify-center gap-4 pt-2">
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export as PDF
          </Button>
          <Button variant="outline" size="sm">
            <FileText className="h-4 w-4 mr-2" />
            Copy Summary
          </Button>
        </div>

        {/* Navigation Section */}
        {(onProcessNext || onProcessPrevious) && (
          <>
            <Separator />
            <div className="space-y-4">
              {/* Progress Stats */}
              {(remainingCount > 0 || completedCount > 0) && (
                <div className="flex items-center justify-center gap-4 text-sm">
                  <Badge variant="secondary" className="gap-1.5">
                    <ListChecks className="h-3.5 w-3.5" />
                    {completedCount} completed
                  </Badge>
                  {remainingCount > 0 && (
                    <Badge variant="outline" className="gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      {remainingCount} remaining
                    </Badge>
                  )}
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex items-center justify-center gap-4">
                {onProcessPrevious && (
                  <Button
                    variant="outline"
                    onClick={onProcessPrevious}
                    disabled={!hasPreviousPatient || countdown !== null}
                  >
                    <ChevronLeft className="h-4 w-4 mr-2" />
                    Process Previous Patient
                  </Button>
                )}
                
                {onProcessNext && (
                  <Button
                    variant="default"
                    onClick={onProcessNext}
                    disabled={!hasNextPatient || countdown !== null}
                    className="relative"
                  >
                    Process Next Patient
                    <ChevronRight className="h-4 w-4 ml-2" />
                    {countdown !== null && (
                      <Badge 
                        variant="secondary" 
                        className="absolute -top-2 -right-2 h-6 w-6 p-0 flex items-center justify-center"
                      >
                        {countdown}
                      </Badge>
                    )}
                  </Button>
                )}
              </div>

              {/* Auto-advance Option */}
              {onAutoAdvanceChange && hasNextPatient && (
                <div className="flex items-center justify-center gap-2">
                  <Checkbox
                    id="auto-advance"
                    checked={autoAdvance}
                    onCheckedChange={onAutoAdvanceChange}
                  />
                  <label 
                    htmlFor="auto-advance" 
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    Automatically proceed to next patient
                  </label>
                  {countdown !== null && (
                    <Badge variant="outline" className="gap-1">
                      <Timer className="h-3 w-3" />
                      {countdown}s
                    </Badge>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}