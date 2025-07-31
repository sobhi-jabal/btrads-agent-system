'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calculator, ChevronDown, ChevronUp } from "lucide-react"

export interface CalculationStep {
  id: string
  label: string
  formula: string
  inputs: Record<string, number | string>
  result: number | string
  unit?: string
  explanation?: string
  isThreshold?: boolean
  thresholdValue?: number
  comparisonOperator?: '>' | '<' | '>=' | '<=' | '==='
}

interface CalculationBreakdownProps {
  title: string
  calculations: CalculationStep[]
  showFormulas?: boolean
}

export function CalculationBreakdown({ 
  title, 
  calculations, 
  showFormulas = true 
}: CalculationBreakdownProps) {
  const [expandedSteps, setExpandedSteps] = React.useState<Set<string>>(new Set())
  const [showAllFormulas, setShowAllFormulas] = React.useState(showFormulas)

  const toggleStepExpansion = (stepId: string) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(stepId)) {
        newSet.delete(stepId)
      } else {
        newSet.add(stepId)
      }
      return newSet
    })
  }

  const formatValue = (value: number | string, unit?: string) => {
    if (typeof value === 'number') {
      const formatted = value % 1 === 0 ? value.toString() : value.toFixed(2)
      return unit ? `${formatted} ${unit}` : formatted
    }
    return value
  }

  const getThresholdStatus = (step: CalculationStep) => {
    if (!step.isThreshold || step.thresholdValue === undefined || step.comparisonOperator === undefined) {
      return null
    }

    const result = typeof step.result === 'number' ? step.result : parseFloat(step.result.toString())
    const threshold = step.thresholdValue
    
    // Skip if result is not a valid number
    if (isNaN(result)) {
      return null
    }
    
    let passes = false
    let statusText = ''
    
    switch (step.comparisonOperator) {
      case '>': 
        passes = result > threshold
        statusText = passes ? 'Exceeds progression threshold' : 'Below progression threshold'
        break
      case '<': 
        passes = result < threshold
        statusText = passes ? 'Exceeds improvement threshold' : 'Above improvement threshold'
        break
      case '>=': 
        passes = result >= threshold
        statusText = passes ? 'Meets measurable disease threshold' : 'Below measurable disease threshold'
        break
      case '<=': passes = result <= threshold; break
      case '===': passes = result === threshold; break
    }

    return {
      passes,
      text: statusText || `${formatValue(result, step.unit)} ${step.comparisonOperator} ${formatValue(threshold, step.unit)}`
    }
  }

  const renderFormulaWithInputs = (step: CalculationStep) => {
    let formula = step.formula
    
    // Replace variable names with actual values
    Object.entries(step.inputs).forEach(([key, value]) => {
      const displayValue = typeof value === 'number' ? value.toFixed(2) : value
      formula = formula.replace(new RegExp(`\\b${key}\\b`, 'g'), displayValue.toString())
    })

    return formula
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Calculator className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {calculations.map((step, index) => {
          const isExpanded = expandedSteps.has(step.id)
          const thresholdStatus = getThresholdStatus(step)

          return (
            <Card key={step.id} className="border-l-4 border-l-blue-500">
              <CardHeader 
                className="cursor-pointer hover:bg-muted/30 transition-colors pb-3"
                onClick={() => toggleStepExpansion(step.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="text-xs font-mono">
                      {index + 1}
                    </Badge>
                    <div>
                      <CardTitle className="text-base">{step.label}</CardTitle>
                      {step.explanation && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {step.explanation}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-right">
                      <div className="font-mono text-lg font-bold">
                        {formatValue(step.result, step.unit)}
                      </div>
                      {thresholdStatus && (
                        <Badge 
                          variant={thresholdStatus.passes ? "default" : "secondary"}
                          className="text-xs mt-1"
                        >
                          {thresholdStatus.passes ? 
                            (step.comparisonOperator === '<' ? '✅ Improvement' : 
                             step.comparisonOperator === '>=' ? '✅ Measurable' :
                             '✅ Progression') : 
                            (step.comparisonOperator === '>=' ? '❌ Not Measurable' : '⚪ Stable')}
                        </Badge>
                      )}
                    </div>
                    {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </div>
                </div>
              </CardHeader>

              {(isExpanded || showAllFormulas) && (
                <CardContent className="pt-0 space-y-3">
                  {/* Formula */}
                  <div>
                    <h5 className="font-medium text-sm mb-2">Formula:</h5>
                    <code className="block p-2 bg-muted/50 rounded text-sm font-mono">
                      {step.formula}
                    </code>
                  </div>

                  {/* Inputs */}
                  <div>
                    <h5 className="font-medium text-sm mb-2">Input Values:</h5>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(step.inputs).map(([key, value]) => (
                        <div key={key} className="flex justify-between p-2 bg-muted/30 rounded text-sm">
                          <span className="font-medium">{key}:</span>
                          <span className="font-mono">{formatValue(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Calculation with substituted values */}
                  <div>
                    <h5 className="font-medium text-sm mb-2">Calculation:</h5>
                    <code className="block p-2 bg-green-50 dark:bg-green-950/20 rounded text-sm font-mono">
                      {renderFormulaWithInputs(step)} = {formatValue(step.result, step.unit)}
                    </code>
                  </div>

                  {/* Threshold explanation */}
                  {step.isThreshold && thresholdStatus && (
                    <div className={`p-2 rounded ${thresholdStatus.passes ? 'bg-green-50 dark:bg-green-950/20' : 'bg-gray-50 dark:bg-gray-950/20'}`}>
                      <p className="text-sm">
                        <span className="font-medium">BT-RADS Threshold: </span>
                        {step.comparisonOperator === '<' && step.thresholdValue! < 0 ? 
                          `>10% decrease required for improvement` :
                          step.comparisonOperator === '>' && step.thresholdValue! > 0 ?
                          `>10% increase required for progression` :
                          step.comparisonOperator === '>=' ?
                          `≥1 mL absolute change required (measurable disease = 1×1×1 cm)` :
                          `${formatValue(Math.abs(step.thresholdValue!), step.unit)} threshold`
                        }
                        <span className={`ml-2 font-medium ${thresholdStatus.passes ? 'text-green-600' : 'text-gray-600'}`}>
                          → {thresholdStatus.text}
                        </span>
                      </p>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          )
        })}

        {calculations.length === 0 && (
          <div className="text-center p-8 text-muted-foreground">
            <Calculator className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No calculations available for this step</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}