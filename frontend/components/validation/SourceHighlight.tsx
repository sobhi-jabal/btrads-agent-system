'use client'

import React from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

interface HighlightedSource {
  text: string
  start_char: number
  end_char: number
  confidence: number
}

interface SourceHighlightProps {
  highlight: HighlightedSource
  index: number
  fullText?: string
  showContext?: boolean
}

export function SourceHighlight({ 
  highlight, 
  index, 
  fullText,
  showContext = false 
}: SourceHighlightProps) {
  const confidenceLevel = highlight.confidence > 0.8 ? 'high' : 
                         highlight.confidence > 0.5 ? 'medium' : 'low'
  
  const confidenceColors = {
    high: 'bg-green-100 border-green-300 text-green-800',
    medium: 'bg-amber-100 border-amber-300 text-amber-800',
    low: 'bg-red-100 border-red-300 text-red-800'
  }

  const getContextText = () => {
    if (!fullText || !showContext) return null
    
    const contextLength = 50
    const start = Math.max(0, highlight.start_char - contextLength)
    const end = Math.min(fullText.length, highlight.end_char + contextLength)
    
    const before = fullText.substring(start, highlight.start_char)
    const highlighted = fullText.substring(highlight.start_char, highlight.end_char)
    const after = fullText.substring(highlight.end_char, end)
    
    return (
      <span className="text-sm">
        {start > 0 && '...'}
        <span className="text-slate-500">{before}</span>
        <mark className="bg-yellow-200 font-medium px-0.5">{highlighted}</mark>
        <span className="text-slate-500">{after}</span>
        {end < fullText.length && '...'}
      </span>
    )
  }

  return (
    <div className="mb-4 last:mb-0">
      <div className="flex items-start gap-3">
        <Badge variant="outline" className="shrink-0 mt-0.5">
          #{index + 1}
        </Badge>
        <div className="flex-1">
          <blockquote 
            className={cn(
              "border-l-4 pl-4 py-2 italic",
              confidenceColors[confidenceLevel].replace('bg-', 'border-l-')
            )}
          >
            {showContext && fullText ? (
              getContextText()
            ) : (
              <span className="text-sm">{highlight.text}</span>
            )}
          </blockquote>
          <div className="flex items-center gap-2 mt-2">
            <Badge 
              variant="secondary" 
              className={cn("text-xs", confidenceColors[confidenceLevel])}
            >
              {Math.round(highlight.confidence * 100)}% relevant
            </Badge>
            <span className="text-xs text-slate-500">
              Characters {highlight.start_char}-{highlight.end_char}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}