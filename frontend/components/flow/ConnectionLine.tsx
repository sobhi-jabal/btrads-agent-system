'use client'

import React from 'react'
import { ArrowDown, ArrowRight, CheckCircle, Clock } from 'lucide-react'

interface ConnectionLineProps {
  isActive: boolean
  isCompleted: boolean
  direction?: 'down' | 'right'
  label?: string
}

export function ConnectionLine({ 
  isActive, 
  isCompleted, 
  direction = 'down',
  label 
}: ConnectionLineProps) {
  const lineColor = isCompleted ? 'border-green-500' : 
                   isActive ? 'border-blue-500 animate-pulse' : 
                   'border-muted'
  
  const iconColor = isCompleted ? 'text-green-500' : 
                   isActive ? 'text-blue-500' : 
                   'text-muted-foreground'

  if (direction === 'right') {
    return (
      <div className="flex items-center justify-center py-2">
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border-2 ${lineColor} bg-background`}>
          {isCompleted ? (
            <CheckCircle className={`h-4 w-4 ${iconColor}`} />
          ) : isActive ? (
            <Clock className={`h-4 w-4 ${iconColor} animate-pulse`} />
          ) : (
            <ArrowRight className={`h-4 w-4 ${iconColor}`} />
          )}
          {label && (
            <span className={`text-xs font-medium ${iconColor}`}>
              {label}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center py-2">
      <div className={`w-px h-6 ${lineColor.replace('border-', 'bg-')}`} />
      <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${lineColor} bg-background`}>
        {isCompleted ? (
          <CheckCircle className={`h-4 w-4 ${iconColor}`} />
        ) : isActive ? (
          <Clock className={`h-4 w-4 ${iconColor} animate-pulse`} />
        ) : (
          <ArrowDown className={`h-4 w-4 ${iconColor}`} />
        )}
      </div>
      <div className={`w-px h-6 ${lineColor.replace('border-', 'bg-')}`} />
      {label && (
        <div className={`mt-1 px-2 py-1 rounded text-xs font-medium ${iconColor} bg-muted/50`}>
          {label}
        </div>
      )}
    </div>
  )
}