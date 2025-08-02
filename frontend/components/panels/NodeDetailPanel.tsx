'use client'

import React from 'react'
import { X } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useBTRADSStore } from '@/lib/stores/btrads-store'
import { cn } from '@/lib/utils'

interface NodeDetailPanelProps {
  nodeId: string | null
  open: boolean
  onClose: () => void
}

export function NodeDetailPanel({ nodeId, open, onClose }: NodeDetailPanelProps) {
  const { agentResults, nodeStatuses } = useBTRADSStore()
  
  if (!nodeId || !open) return null
  
  const result = agentResults[nodeId]
  const status = nodeStatuses[nodeId] || 'pending'
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50'
      case 'active': return 'text-blue-600 bg-blue-50'
      case 'error': return 'text-red-600 bg-red-50'
      case 'needs-validation': return 'text-amber-600 bg-amber-50'
      default: return 'text-slate-600 bg-slate-50'
    }
  }
  
  return (
    <div className={cn(
      "fixed right-0 top-0 h-full w-96 bg-background border-l shadow-lg transform transition-transform",
      open ? "translate-x-0" : "translate-x-full"
    )}>
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-lg font-semibold">Node Details</h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
      
      <ScrollArea className="h-[calc(100vh-80px)]">
        <div className="p-4 space-y-4">
          {/* Node Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Node Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">ID</span>
                <span className="font-mono text-sm">{nodeId}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge className={getStatusColor(status)}>
                  {status}
                </Badge>
              </div>
            </CardContent>
          </Card>
          
          {/* Agent Result */}
          {result && (
            <>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Extraction Result</CardTitle>
                  <CardDescription>
                    Agent: {result.agent_id}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <span className="text-sm font-medium">Value</span>
                    <div className="mt-1 p-2 bg-muted rounded text-sm font-mono">
                      {JSON.stringify(result.extracted_value)}
                    </div>
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium">Confidence</span>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500"
                          style={{ width: `${result.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {Math.round(result.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  {result.reasoning && (
                    <div>
                      <span className="text-sm font-medium">Reasoning</span>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {result.reasoning}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Source Highlights */}
              {result.source_highlights && result.source_highlights.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">Source Evidence</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {result.source_highlights.map((highlight: any, idx: number) => (
                      <div key={idx} className="p-2 bg-muted rounded">
                        <p className="text-sm italic">"{highlight.text}"</p>
                        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                          <span>Characters {highlight.start_char}-{highlight.end_char}</span>
                          <Badge variant="outline" className="text-xs">
                            {Math.round(highlight.confidence * 100)}% relevant
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
              
              {/* Missing Information */}
              {result.missing_info && result.missing_info.length > 0 && (
                <Card className="border-amber-200 bg-amber-50">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm text-amber-900">
                      Missing Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {result.missing_info.map((info: any, idx: number) => (
                      <div key={idx} className="text-sm text-amber-800">
                        <p className="font-medium">{info.field}</p>
                        <p className="text-xs mt-1">{info.reason}</p>
                        {info.suggested_fallback && (
                          <p className="text-xs mt-1 italic">
                            Fallback: {info.suggested_fallback}
                          </p>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
              
              {/* Processing Metadata */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Model</span>
                    <span className="font-mono">{result.llm_model}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Processing Time</span>
                    <span>{result.processing_time_ms}ms</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Timestamp</span>
                    <span className="text-xs">
                      {new Date(result.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}