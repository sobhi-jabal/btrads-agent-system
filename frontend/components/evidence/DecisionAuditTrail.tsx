'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { 
  GitBranch, 
  ArrowRight, 
  ArrowDown, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Eye,
  EyeOff
} from "lucide-react"

export interface DecisionCriteria {
  id: string
  condition: string
  value: any
  threshold?: any
  operator?: string
  met: boolean
  reasoning: string
}

export interface AlternativePath {
  nodeId: string
  label: string
  reason: string
  wouldLeadTo: string
}

export interface DecisionPoint {
  id: string
  nodeId: string
  label: string
  description: string
  criteria: DecisionCriteria[]
  selectedPath: string
  alternativePaths: AlternativePath[]
  confidence: number
  reasoning: string
}

interface DecisionAuditTrailProps {
  decisions: DecisionPoint[]
  currentNodeId?: string
  showAlternatives?: boolean
}

export function DecisionAuditTrail({ 
  decisions, 
  currentNodeId,
  showAlternatives = true
}: DecisionAuditTrailProps) {
  const [expandedDecisions, setExpandedDecisions] = React.useState<Set<string>>(new Set())
  const [showAlternativePaths, setShowAlternativePaths] = React.useState(showAlternatives)

  const toggleDecisionExpansion = (decisionId: string) => {
    setExpandedDecisions(prev => {
      const newSet = new Set(prev)
      if (newSet.has(decisionId)) {
        newSet.delete(decisionId)
      } else {
        newSet.add(decisionId)
      }
      return newSet
    })
  }

  const getCriteriaIcon = (met: boolean) => {
    return met ? (
      <CheckCircle className="h-4 w-4 text-green-500" />
    ) : (
      <XCircle className="h-4 w-4 text-red-500" />
    )
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600 bg-green-50 border-green-200'
    if (confidence >= 70) return 'text-blue-600 bg-blue-50 border-blue-200'
    if (confidence >= 50) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    return 'text-red-600 bg-red-50 border-red-200'
  }

  const formatValue = (value: any) => {
    if (typeof value === 'number') {
      return value % 1 === 0 ? value.toString() : value.toFixed(2)
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No'
    }
    return value?.toString() || 'N/A'
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Decision Audit Trail
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAlternativePaths(!showAlternativePaths)}
          >
            {showAlternativePaths ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            {showAlternativePaths ? 'Hide' : 'Show'} Alternatives
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {decisions.map((decision, index) => {
          const isExpanded = expandedDecisions.has(decision.id)
          const isCurrent = decision.nodeId === currentNodeId
          const metCriteria = decision.criteria.filter(c => c.met).length
          const totalCriteria = decision.criteria.length

          return (
            <div key={decision.id} className="relative">
              <Card className={`border-l-4 ${
                isCurrent ? 'border-l-blue-500 bg-blue-50/30' : 'border-l-gray-300'
              }`}>
                <CardHeader 
                  className="cursor-pointer hover:bg-muted/30 transition-colors pb-3"
                  onClick={() => toggleDecisionExpansion(decision.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="font-mono text-xs">
                        {index + 1}
                      </Badge>
                      <div>
                        <CardTitle className="text-base">{decision.label}</CardTitle>
                        <p className="text-sm text-muted-foreground mt-1">
                          {decision.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant="outline" 
                        className={`${getConfidenceColor(decision.confidence)} border`}
                      >
                        {decision.confidence}% confident
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {metCriteria}/{totalCriteria} criteria met
                      </Badge>
                      {isExpanded ? (
                        <ArrowDown className="h-4 w-4" />
                      ) : (
                        <ArrowRight className="h-4 w-4" />
                      )}
                    </div>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent className="pt-0 space-y-4">
                    {/* Decision criteria */}
                    <div>
                      <h4 className="font-medium text-sm mb-3">Decision Criteria:</h4>
                      <div className="space-y-2">
                        {decision.criteria.map(criteria => (
                          <div 
                            key={criteria.id}
                            className={`p-3 rounded border ${
                              criteria.met ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              {getCriteriaIcon(criteria.met)}
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-medium text-sm">{criteria.condition}</span>
                                  {criteria.threshold && (
                                    <code className="text-xs bg-muted px-1 py-0.5 rounded">
                                      {formatValue(criteria.value)} {criteria.operator} {formatValue(criteria.threshold)}
                                    </code>
                                  )}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {criteria.reasoning}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Decision reasoning */}
                    <div>
                      <h4 className="font-medium text-sm mb-2">Decision Logic:</h4>
                      <p className="text-sm text-muted-foreground p-3 bg-muted/30 rounded">
                        {decision.reasoning}
                      </p>
                    </div>

                    {/* Selected path */}
                    <div>
                      <h4 className="font-medium text-sm mb-2">Selected Path:</h4>
                      <div className="flex items-center gap-2 p-2 bg-green-50 border border-green-200 rounded">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="font-medium text-green-700">{decision.selectedPath}</span>
                      </div>
                    </div>

                    {/* Alternative paths */}
                    {showAlternativePaths && decision.alternativePaths.length > 0 && (
                      <div>
                        <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-orange-500" />
                          Alternative Paths Not Taken:
                        </h4>
                        <div className="space-y-2">
                          {decision.alternativePaths.map(alt => (
                            <div 
                              key={alt.nodeId}
                              className="p-2 bg-orange-50 border border-orange-200 rounded opacity-75"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-orange-700">{alt.label}</span>
                                <Badge variant="outline" className="text-xs">
                                  Would lead to: {alt.wouldLeadTo}
                                </Badge>
                              </div>
                              <p className="text-xs text-orange-600 mt-1">
                                Not selected because: {alt.reason}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>

              {/* Arrow to next decision */}
              {index < decisions.length - 1 && (
                <div className="flex justify-center my-2">
                  <ArrowDown className="h-5 w-5 text-muted-foreground" />
                </div>
              )}
            </div>
          )
        })}

        {decisions.length === 0 && (
          <div className="text-center p-8 text-muted-foreground">
            <GitBranch className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No decision points recorded yet</p>
            <p className="text-sm">Decisions will appear here as the analysis progresses</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}