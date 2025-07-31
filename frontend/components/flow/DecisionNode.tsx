'use client'

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  CheckCircle, 
  Clock, 
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  FileText,
  Activity,
  Database,
  Stethoscope,
  Calendar,
  Pill,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus
} from "lucide-react"

export interface DecisionNodeData {
  nodeId: string
  label: string
  type: 'data-extraction' | 'decision' | 'outcome'
  status: 'pending' | 'processing' | 'completed' | 'error'
  btradsScore?: string
  data?: Record<string, any>
  reasoning?: string
  nextNode?: string
  selectedPath?: string
  options?: Array<{
    label: string
    value: string
    nextNode: string
    condition?: string
  }>
}

interface DecisionNodeProps {
  node: DecisionNodeData
  isExpanded: boolean
  isCurrent: boolean
  onToggleExpand: () => void
  onPathSelect?: (path: string) => void
}

export function DecisionNode({ 
  node, 
  isExpanded, 
  isCurrent, 
  onToggleExpand,
  onPathSelect 
}: DecisionNodeProps) {

  const getStatusIcon = (status: DecisionNodeData['status']) => {
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

  const getTypeIcon = (type: DecisionNodeData['type']) => {
    switch (type) {
      case 'data-extraction':
        return <FileText className="h-4 w-4 text-blue-600" />
      case 'decision':
        return <Activity className="h-4 w-4 text-orange-600" />
      case 'outcome':
        return <Database className="h-4 w-4 text-green-600" />
      default:
        return <Stethoscope className="h-4 w-4 text-gray-600" />
    }
  }

  const getSpecificIcon = (nodeId: string) => {
    switch (nodeId) {
      case 'node_1_suitable_prior':
        return <Calendar className="h-4 w-4" />
      case 'node_2_imaging_assessment':
        return <TrendingUp className="h-4 w-4" />
      case 'node_3a_medications':
      case 'node_3b_avastin_response':
      case 'node_3c_steroid_effects':
        return <Pill className="h-4 w-4" />
      case 'node_4_time_since_xrt':
        return <Zap className="h-4 w-4" />
      default:
        return getTypeIcon(node.type)
    }
  }

  const getTrendIcon = (value: number) => {
    if (value > 10) return <TrendingUp className="h-4 w-4 text-red-500" />
    if (value < -10) return <TrendingDown className="h-4 w-4 text-green-500" />
    return <Minus className="h-4 w-4 text-gray-500" />
  }

  const getBTRADSColor = (score?: string) => {
    if (!score) return 'default'
    
    switch (score) {
      case '0': return 'secondary'
      case '1a':
      case '1b': return 'default'
      case '2': return 'outline'
      case '3a':
      case '3b':
      case '3c': return 'destructive'
      case '4': return 'destructive'
      default: return 'default'
    }
  }

  return (
    <Card className={`transition-all duration-300 ${
      isCurrent ? 'ring-2 ring-blue-500 shadow-lg' : 
      node.status === 'completed' ? 'border-green-200 bg-green-50/30 dark:bg-green-950/10' :
      node.status === 'error' ? 'border-red-200 bg-red-50/30 dark:bg-red-950/10' :
      node.status === 'processing' ? 'border-blue-200 bg-blue-50/30 dark:bg-blue-950/10' :
      'border-muted'
    }`}>
      <CardHeader 
        className="cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {getStatusIcon(node.status)}
              <Badge variant={node.type === 'outcome' ? getBTRADSColor(node.btradsScore) : 'secondary'}>
                {node.type.replace('-', ' ')}
              </Badge>
            </div>
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                {getSpecificIcon(node.nodeId)}
                {node.label}
                {node.selectedPath && (
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                )}
                {node.selectedPath && (
                  <Badge variant="outline" className="text-xs">
                    {node.selectedPath}
                  </Badge>
                )}
              </CardTitle>
              {node.btradsScore && node.status === 'completed' && (
                <Badge variant={getBTRADSColor(node.btradsScore)} className="mt-1">
                  BT-RADS {node.btradsScore}
                </Badge>
              )}
            </div>
          </div>
          {(node.status === 'completed' || node.data) && (
            isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
          )}
        </div>
      </CardHeader>
      
      {isExpanded && (node.status === 'completed' || node.data) && (
        <>
          <Separator />
          <CardContent className="pt-4 space-y-4">
            {/* Reasoning */}
            {node.reasoning && (
              <div>
                <h4 className="font-medium text-sm mb-2 text-foreground">Reasoning:</h4>
                <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md">
                  {node.reasoning}
                </p>
              </div>
            )}
            
            {/* Specific Node Data Display */}
            {node.data && (
              <div>
                <h4 className="font-medium text-sm mb-3 text-foreground">
                  {node.type === 'data-extraction' ? 'Extracted Data:' : 
                   node.type === 'decision' ? 'Decision Criteria:' : 'Results:'}
                </h4>
                
                {/* Custom data display based on node type */}
                {node.nodeId === 'node_2_imaging_assessment' && node.data && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-muted/30 p-3 rounded-md">
                        <div className="flex items-center gap-2 mb-1">
                          {getTrendIcon(node.data.flairChange)}
                          <span className="font-medium text-sm">FLAIR Change</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{node.data.flairVolume}</p>
                        <p className="text-lg font-semibold">{node.data.flairChange}%</p>
                      </div>
                      <div className="bg-muted/30 p-3 rounded-md">
                        <div className="flex items-center gap-2 mb-1">
                          {getTrendIcon(node.data.enhChange)}
                          <span className="font-medium text-sm">Enhancement Change</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{node.data.enhVolume}</p>
                        <p className="text-lg font-semibold">{node.data.enhChange}%</p>
                      </div>
                    </div>
                    <div className="text-center p-2 bg-primary/10 rounded-md">
                      <Badge variant="outline" className="text-sm">
                        Assessment: {node.data.assessment}
                      </Badge>
                    </div>
                  </div>
                )}
                
                {/* Generic data display for other nodes */}
                {node.nodeId !== 'node_2_imaging_assessment' && (
                  <div className="grid grid-cols-1 gap-2">
                    {Object.entries(node.data).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center p-2 bg-muted/30 rounded">
                        <span className="font-medium text-sm capitalize">
                          {key.replace(/([A-Z])/g, ' $1').toLowerCase()}:
                        </span>
                        <span className="text-sm text-muted-foreground font-mono">
                          {String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Decision Options */}
            {node.options && node.status === 'processing' && onPathSelect && (
              <div>
                <h4 className="font-medium text-sm mb-3 text-foreground">Choose Path:</h4>
                <div className="space-y-2">
                  {node.options.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => onPathSelect(option.value)}
                      className="w-full text-left p-3 rounded-md border border-muted hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{option.label}</span>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                      {option.condition && (
                        <p className="text-xs text-muted-foreground mt-1">{option.condition}</p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Next Step Indicator */}
            {node.nextNode && node.status === 'completed' && (
              <div className="pt-2 border-t border-muted">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <ArrowRight className="h-4 w-4" />
                  <span>Next: {node.nextNode.replace(/_/g, ' ').replace(/node |outcome /, '')}</span>
                </div>
              </div>
            )}
          </CardContent>
        </>
      )}
    </Card>
  )
}