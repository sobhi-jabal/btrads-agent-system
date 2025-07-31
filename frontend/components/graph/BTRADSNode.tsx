'use client'

import React, { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { 
  CheckCircle2, 
  Circle, 
  AlertCircle, 
  Loader2,
  FileQuestion,
  Activity,
  ChevronRight
} from 'lucide-react'
import { cn } from '@/lib/utils'

export interface BTRADSNodeData {
  label: string
  type: 'decision' | 'outcome' | 'data-extraction'
  status: 'pending' | 'active' | 'completed' | 'error' | 'needs-validation'
  isActive: boolean
  isInPath: boolean
  btradsScore?: string
  confidence?: number
  extractedValue?: any
}

export const BTRADSNode = memo(({ data, selected }: NodeProps<BTRADSNodeData>) => {
  const getStatusIcon = () => {
    switch (data.status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-success" />
      case 'active':
        return <Loader2 className="w-4 h-4 text-primary animate-spin" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error" />
      case 'needs-validation':
        return <FileQuestion className="w-4 h-4 text-warning animate-pulse" />
      default:
        return <Circle className="w-4 h-4 text-muted-foreground/50" />
    }
  }

  const getNodeStyle = () => {
    const baseClasses = 'px-6 py-4 rounded-lg border transition-all duration-200 min-w-[240px] shadow-soft hover:shadow-soft-lg'
    
    // Major decision nodes
    if (data.type === 'decision' && (
      data.label.includes('Suitable Prior') || 
      data.label.includes('Imaging Assessment') ||
      data.label.includes('Time Since XRT')
    )) {
      return cn(
        baseClasses,
        'bg-primary text-primary-foreground border-2 border-primary',
        data.status === 'active' && 'scale-105 shadow-lg',
        data.isInPath && 'ring-2 ring-primary/20 ring-offset-2',
        !data.isInPath && 'opacity-60'
      )
    }
    
    // Outcome nodes (BT-RADS scores)
    if (data.type === 'outcome') {
      return cn(
        baseClasses,
        'bg-card border-2',
        data.status === 'completed' ? 'border-success bg-success/5' : 'border-border',
        data.isInPath && 'ring-2 ring-primary/20 ring-offset-2',
        !data.isInPath && 'opacity-60'
      )
    }

    // Secondary nodes
    return cn(
      baseClasses,
      'bg-secondary text-secondary-foreground border border-border',
      data.status === 'active' && 'border-primary shadow-lg',
      data.isInPath && 'border-solid',
      !data.isInPath && 'border-dashed opacity-50',
      selected && 'ring-2 ring-primary/30 ring-offset-2'
    )
  }

  const isDecisionNode = data.type === 'decision'
  const isMajorNode = isDecisionNode && (
    data.label.includes('Suitable Prior') || 
    data.label.includes('Imaging Assessment') ||
    data.label.includes('Time Since XRT')
  )

  return (
    <>
      <Handle 
        type="target" 
        position={Position.Top} 
        className="!bg-muted-foreground/20 !border-muted-foreground/40" 
      />
      
      <div className={getNodeStyle()}>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className={cn(
              "font-semibold",
              isMajorNode ? "text-base" : "text-sm"
            )}>
              {data.label}
            </h3>
            {getStatusIcon()}
          </div>
          
          {data.type === 'outcome' && data.btradsScore && (
            <div className="text-2xl font-bold mt-2">
              BT-{data.btradsScore}
            </div>
          )}
          
          {data.extractedValue && data.status === 'completed' && (
            <div className="mt-3 p-2 bg-muted/50 rounded text-xs">
              <span className="font-medium">Result:</span> {data.extractedValue}
              {data.confidence !== undefined && (
                <span className="ml-2 text-muted-foreground">
                  ({Math.round(data.confidence * 100)}%)
                </span>
              )}
            </div>
          )}
          
          {data.status === 'needs-validation' && (
            <div className="mt-3 p-2 bg-warning/10 rounded text-xs text-warning-foreground">
              Validation required
            </div>
          )}
          
          {data.type === 'decision' && data.isActive && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2">
              Processing decision
              <ChevronRight className="w-3 h-3" />
            </div>
          )}
        </div>
      </div>
      
      <Handle 
        type="source" 
        position={Position.Bottom} 
        className="!bg-muted-foreground/20 !border-muted-foreground/40" 
      />
    </>
  )
})

BTRADSNode.displayName = 'BTRADSNode'