'use client'

import React from 'react'
import { Badge } from "@/components/ui/badge"
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Info,
  User,
  Bot,
  HelpCircle
} from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface DataConfidenceBadgeProps {
  confidence?: number
  source?: 'nlp' | 'llm' | 'user' | 'manual'
  isMissing?: boolean
  field: string
  value?: any
  onRequestManualInput?: () => void
}

export function DataConfidenceBadge({ 
  confidence = 0, 
  source, 
  isMissing,
  field,
  value,
  onRequestManualInput
}: DataConfidenceBadgeProps) {
  // Determine badge variant and icon based on confidence
  const getBadgeProps = () => {
    if (source === 'user' || source === 'manual') {
      return {
        variant: 'default' as const,
        icon: <User className="h-3 w-3" />,
        text: 'User Provided',
        className: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400'
      }
    }

    if (isMissing) {
      return {
        variant: 'destructive' as const,
        icon: <XCircle className="h-3 w-3" />,
        text: 'Missing',
        className: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-400'
      }
    }

    if (confidence >= 90) {
      return {
        variant: 'default' as const,
        icon: <CheckCircle className="h-3 w-3" />,
        text: 'High Confidence',
        className: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-400'
      }
    } else if (confidence >= 70) {
      return {
        variant: 'secondary' as const,
        icon: <Info className="h-3 w-3" />,
        text: 'Good Confidence',
        className: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400'
      }
    } else if (confidence >= 50) {
      return {
        variant: 'outline' as const,
        icon: <AlertTriangle className="h-3 w-3" />,
        text: 'Low Confidence',
        className: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-400'
      }
    } else {
      return {
        variant: 'destructive' as const,
        icon: <HelpCircle className="h-3 w-3" />,
        text: 'Very Low Confidence',
        className: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400'
      }
    }
  }

  const { variant, icon, text, className } = getBadgeProps()
  const sourceIcon = source === 'llm' ? <Bot className="h-3 w-3" /> : null

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge 
            variant={variant}
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium cursor-help ${className}`}
            onClick={onRequestManualInput}
          >
            {icon}
            {confidence > 0 && !isMissing && (
              <span>{confidence}%</span>
            )}
            {sourceIcon}
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-sm">
          <div className="space-y-2">
            <div className="font-medium">{field}</div>
            {value && (
              <div className="text-xs text-muted-foreground">
                Value: {typeof value === 'object' ? JSON.stringify(value) : value}
              </div>
            )}
            <div className="text-xs">
              <div>{text}</div>
              {source && <div>Source: {source.toUpperCase()}</div>}
              {!isMissing && confidence > 0 && (
                <div>Confidence: {confidence}%</div>
              )}
            </div>
            {onRequestManualInput && confidence < 70 && (
              <div className="text-xs text-blue-600 dark:text-blue-400 pt-1 border-t">
                Click to provide manual input
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}