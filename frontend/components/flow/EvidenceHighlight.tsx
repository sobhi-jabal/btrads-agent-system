import React, { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Info, Brain, Calendar, Pill } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

interface Evidence {
  type: string
  text: string
  mention?: string
  date?: string
  start_pos: number
  end_pos: number
  context_start: number
  context_end: number
  relevance: number
  source: string
}

interface EvidenceHighlightProps {
  clinicalNote: string
  evidence: Evidence[]
  extractionType: 'medications' | 'radiation_date'
}

export const EvidenceHighlight: React.FC<EvidenceHighlightProps> = ({
  clinicalNote,
  evidence,
  extractionType
}) => {
  // Sort evidence by position for proper highlighting
  const sortedEvidence = useMemo(() => 
    [...evidence].sort((a, b) => a.start_pos - b.start_pos),
    [evidence]
  )

  // Create highlighted segments
  const highlightedSegments = useMemo(() => {
    const segments: Array<{ text: string; highlighted: boolean; evidence?: Evidence }> = []
    let lastPos = 0

    sortedEvidence.forEach((ev) => {
      // Add non-highlighted text before this evidence
      if (ev.start_pos > lastPos) {
        segments.push({
          text: clinicalNote.slice(lastPos, ev.start_pos),
          highlighted: false
        })
      }

      // Add highlighted evidence
      segments.push({
        text: clinicalNote.slice(ev.start_pos, ev.end_pos),
        highlighted: true,
        evidence: ev
      })

      lastPos = ev.end_pos
    })

    // Add remaining text
    if (lastPos < clinicalNote.length) {
      segments.push({
        text: clinicalNote.slice(lastPos),
        highlighted: false
      })
    }

    return segments
  }, [clinicalNote, sortedEvidence])

  // Get color based on evidence type
  const getHighlightColor = (ev: Evidence) => {
    if (extractionType === 'medications') {
      return ev.type === 'steroid' ? 'bg-blue-200' : 'bg-green-200'
    }
    return ev.relevance > 0.8 ? 'bg-yellow-200' : 'bg-gray-200'
  }

  // Get icon based on evidence type
  const getIcon = (ev: Evidence) => {
    if (extractionType === 'medications') {
      return <Pill className="h-3 w-3" />
    }
    return <Calendar className="h-3 w-3" />
  }

  return (
    <div className="space-y-4">
      {/* Evidence Summary */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Evidence Summary
          </CardTitle>
          <CardDescription>
            Found {evidence.length} relevant {extractionType === 'medications' ? 'medication mentions' : 'date references'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {evidence.map((ev, idx) => (
              <Badge
                key={idx}
                variant="secondary"
                className={`${getHighlightColor(ev)} text-black border-gray-300`}
              >
                {getIcon(ev)}
                <span className="ml-1">
                  {ev.mention || ev.date || ev.type}
                  {' '}
                  ({Math.round((ev.relevance || 0) * 100)}%)
                </span>
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Highlighted Clinical Note */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Info className="h-5 w-5" />
            Clinical Note with Highlights
          </CardTitle>
          <CardDescription>
            Hover over highlighted text to see extraction details
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-96">
            <TooltipProvider>
              <pre className="whitespace-pre-wrap font-mono text-sm">
                {highlightedSegments.map((segment, idx) => (
                  segment.highlighted && segment.evidence ? (
                    <Tooltip key={idx}>
                      <TooltipTrigger asChild>
                        <span
                          className={`${getHighlightColor(segment.evidence)} px-1 rounded cursor-help transition-colors hover:opacity-80`}
                        >
                          {segment.text}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <div className="space-y-1">
                          <div className="font-semibold">
                            {segment.evidence.type === 'steroid' ? 'Steroid Mention' :
                             segment.evidence.type === 'avastin' ? 'Avastin Mention' :
                             'Date Reference'}
                          </div>
                          <div className="text-sm">
                            Relevance: {Math.round((segment.evidence.relevance || 0) * 100)}%
                          </div>
                          <div className="text-sm text-gray-600">
                            Position: {segment.evidence.start_pos}-{segment.evidence.end_pos}
                          </div>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <span key={idx}>{segment.text}</span>
                  )
                ))}
              </pre>
            </TooltipProvider>
          </div>
        </CardContent>
      </Card>

      {/* Evidence Details */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Evidence Details</CardTitle>
          <CardDescription>
            Context and relevance for each extracted piece of evidence
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {evidence.map((ev, idx) => (
            <div key={idx} className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Badge variant="outline" className={getHighlightColor(ev)}>
                  {ev.type}
                </Badge>
                <span className="text-sm text-gray-600">
                  {Math.round((ev.relevance || 0) * 100)}% confidence
                </span>
              </div>
              <div className="text-sm bg-gray-50 p-2 rounded font-mono">
                <span className="text-gray-500">...</span>
                <span className={`${getHighlightColor(ev)} px-1 rounded`}>
                  {ev.text}
                </span>
                <span className="text-gray-500">...</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}