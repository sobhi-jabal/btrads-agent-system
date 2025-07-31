'use client'

import React, { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Search, FileText, Highlighter } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Highlight {
  text: string
  start_char: number
  end_char: number
  confidence: number
}

interface ClinicalNoteViewerProps {
  note: string
  highlights?: Highlight[]
  onTextSelect?: (text: string, start: number, end: number) => void
}

export function ClinicalNoteViewer({ 
  note, 
  highlights = [], 
  onTextSelect 
}: ClinicalNoteViewerProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [searchHighlights, setSearchHighlights] = useState<number[][]>([])
  const contentRef = useRef<HTMLDivElement>(null)

  // Create highlighted text with both agent highlights and search results
  const renderHighlightedText = () => {
    if (!note) return null

    // Combine all highlights
    const allHighlights: Array<{
      start: number
      end: number
      type: 'agent' | 'search'
      confidence?: number
    }> = [
      ...highlights.map(h => ({
        start: h.start_char,
        end: h.end_char,
        type: 'agent' as const,
        confidence: h.confidence
      })),
      ...searchHighlights.map(([start, end]) => ({
        start,
        end,
        type: 'search' as const
      }))
    ]

    // Sort by start position
    allHighlights.sort((a, b) => a.start - b.start)

    const elements: React.ReactNode[] = []
    let lastEnd = 0

    allHighlights.forEach((highlight, idx) => {
      // Add text before highlight
      if (highlight.start > lastEnd) {
        elements.push(
          <span key={`text-${idx}`}>
            {note.substring(lastEnd, highlight.start)}
          </span>
        )
      }

      // Add highlighted text
      const highlightedText = note.substring(highlight.start, highlight.end)
      
      if (highlight.type === 'agent') {
        const confidence = highlight.confidence || 0
        const confidenceClass = confidence > 0.8 ? 'bg-green-200' :
                               confidence > 0.5 ? 'bg-amber-200' : 'bg-red-200'
        
        elements.push(
          <mark
            key={`agent-${idx}`}
            className={cn(
              'px-0.5 rounded cursor-pointer transition-colors',
              confidenceClass,
              'hover:brightness-90'
            )}
            title={`Confidence: ${Math.round(confidence * 100)}%`}
            onClick={() => handleHighlightClick(highlight)}
          >
            {highlightedText}
          </mark>
        )
      } else {
        elements.push(
          <mark
            key={`search-${idx}`}
            className="bg-yellow-300 px-0.5"
          >
            {highlightedText}
          </mark>
        )
      }

      lastEnd = highlight.end
    })

    // Add remaining text
    if (lastEnd < note.length) {
      elements.push(
        <span key="text-end">
          {note.substring(lastEnd)}
        </span>
      )
    }

    return elements
  }

  // Handle text selection
  const handleTextSelection = () => {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) return

    const selectedText = selection.toString()
    const range = selection.getRangeAt(0)
    
    // Calculate character positions
    const preSelectionRange = range.cloneRange()
    preSelectionRange.selectNodeContents(contentRef.current!)
    preSelectionRange.setEnd(range.startContainer, range.startOffset)
    
    const start = preSelectionRange.toString().length
    const end = start + selectedText.length

    if (onTextSelect) {
      onTextSelect(selectedText, start, end)
    }
  }

  // Search functionality
  useEffect(() => {
    if (!searchTerm || !note) {
      setSearchHighlights([])
      return
    }

    const regex = new RegExp(searchTerm, 'gi')
    const matches: number[][] = []
    let match

    while ((match = regex.exec(note)) !== null) {
      matches.push([match.index, match.index + match[0].length])
    }

    setSearchHighlights(matches)
  }, [searchTerm, note])

  const handleHighlightClick = (highlight: any) => {
    // Scroll to highlight if needed
    // Could also show a tooltip with more info
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Clinical Note
          </CardTitle>
          {highlights.length > 0 && (
            <Badge variant="secondary" className="gap-1">
              <Highlighter className="w-3 h-3" />
              {highlights.length} highlights
            </Badge>
          )}
        </div>
        
        {/* Search bar */}
        <div className="relative mt-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search in note..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {searchHighlights.length > 0 && (
            <Badge 
              variant="outline" 
              className="absolute right-2 top-1/2 transform -translate-y-1/2"
            >
              {searchHighlights.length}
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-full">
          <div 
            ref={contentRef}
            className="p-6 text-sm leading-relaxed whitespace-pre-wrap font-mono"
            onMouseUp={handleTextSelection}
          >
            {renderHighlightedText()}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}