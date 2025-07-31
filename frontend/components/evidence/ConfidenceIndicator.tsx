'use client'

import React from 'react'
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { CheckCircle, AlertTriangle, HelpCircle, XCircle } from "lucide-react"

export interface ConfidenceData {
  overall: number // 0-100
  factors: {
    evidenceQuality: number
    dataCompleteness: number
    patternMatches: number
    clinicalCoherence: number
  }
  level: 'very-high' | 'high' | 'medium' | 'low' | 'very-low'
  reasoning: string
  uncertainties?: string[]
  alternatives?: string[]
}

interface ConfidenceIndicatorProps {
  confidence: ConfidenceData
  compact?: boolean
  showDetails?: boolean
}

export function ConfidenceIndicator({ 
  confidence, 
  compact = false, 
  showDetails = true 
}: ConfidenceIndicatorProps) {
  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'very-high': return 'text-green-700 bg-green-100 border-green-300'
      case 'high': return 'text-green-600 bg-green-50 border-green-200'
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'low': return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'very-low': return 'text-red-600 bg-red-50 border-red-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getConfidenceIcon = (level: string) => {
    switch (level) {
      case 'very-high': return <CheckCircle className="h-4 w-4" />
      case 'high': return <CheckCircle className="h-4 w-4" />
      case 'medium': return <AlertTriangle className="h-4 w-4" />
      case 'low': return <HelpCircle className="h-4 w-4" />
      case 'very-low': return <XCircle className="h-4 w-4" />
      default: return <HelpCircle className="h-4 w-4" />
    }
  }

  const getConfidenceLabel = (level: string) => {
    switch (level) {
      case 'very-high': return 'Very High Confidence'
      case 'high': return 'High Confidence'
      case 'medium': return 'Medium Confidence'
      case 'low': return 'Low Confidence'
      case 'very-low': return 'Very Low Confidence'
      default: return 'Unknown Confidence'
    }
  }

  const getProgressColor = (value: number) => {
    if (value >= 80) return 'bg-green-500'
    if (value >= 60) return 'bg-yellow-500'
    if (value >= 40) return 'bg-orange-500'
    return 'bg-red-500'
  }

  if (compact) {
    return (
      <Badge 
        variant="outline" 
        className={`${getConfidenceColor(confidence.level)} border flex items-center gap-1`}
      >
        {getConfidenceIcon(confidence.level)}
        {confidence.overall}%
        <span className="text-xs">confidence</span>
      </Badge>
    )
  }

  return (
    <Card className="w-full">
      <CardContent className="p-4 space-y-4">
        {/* Overall confidence */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getConfidenceIcon(confidence.level)}
            <span className="font-medium">{getConfidenceLabel(confidence.level)}</span>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">{confidence.overall}%</div>
            <div className="text-xs text-muted-foreground">overall confidence</div>
          </div>
        </div>

        {/* Overall progress bar */}
        <div className="space-y-2">
          <Progress 
            value={confidence.overall} 
            className="h-2"
            // Note: Progress component styling will need to be customized for color
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>

        {/* Confidence reasoning */}
        <div className="p-3 bg-muted/30 rounded-lg">
          <h4 className="font-medium text-sm mb-2">Assessment Reasoning:</h4>
          <p className="text-sm text-muted-foreground">{confidence.reasoning}</p>
        </div>

        {showDetails && (
          <>
            {/* Factor breakdown */}
            <div className="space-y-3">
              <h4 className="font-medium text-sm">Confidence Factors:</h4>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Evidence Quality</span>
                  <div className="flex items-center gap-2">
                    <Progress value={confidence.factors.evidenceQuality} className="w-20 h-2" />
                    <span className="font-mono text-xs w-8">{confidence.factors.evidenceQuality}%</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span>Data Completeness</span>
                  <div className="flex items-center gap-2">
                    <Progress value={confidence.factors.dataCompleteness} className="w-20 h-2" />
                    <span className="font-mono text-xs w-8">{confidence.factors.dataCompleteness}%</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span>Pattern Matches</span>
                  <div className="flex items-center gap-2">
                    <Progress value={confidence.factors.patternMatches} className="w-20 h-2" />
                    <span className="font-mono text-xs w-8">{confidence.factors.patternMatches}%</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span>Clinical Coherence</span>
                  <div className="flex items-center gap-2">
                    <Progress value={confidence.factors.clinicalCoherence} className="w-20 h-2" />
                    <span className="font-mono text-xs w-8">{confidence.factors.clinicalCoherence}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Uncertainties */}
            {confidence.uncertainties && confidence.uncertainties.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                  Uncertainties:
                </h4>
                <ul className="space-y-1">
                  {confidence.uncertainties.map((uncertainty, index) => (
                    <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-orange-500 mt-1">•</span>
                      {uncertainty}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Alternative interpretations */}
            {confidence.alternatives && confidence.alternatives.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm flex items-center gap-2">
                  <HelpCircle className="h-4 w-4 text-blue-500" />
                  Alternative Interpretations:
                </h4>
                <ul className="space-y-1">
                  {confidence.alternatives.map((alternative, index) => (
                    <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-blue-500 mt-1">→</span>
                      {alternative}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}