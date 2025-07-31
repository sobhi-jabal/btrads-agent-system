'use client'

import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  CheckCircle2, 
  AlertCircle, 
  FileText,
  Sparkles
} from 'lucide-react'

import { SourceHighlight } from './SourceHighlight'
import { AgentResult } from '@/types/agent'

interface ValidationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  agentResult: AgentResult | null
  onValidate: (value: any, notes?: string) => void
  validationOptions?: Array<{ value: any; label: string; description?: string }>
}

export function ValidationDialog({
  open,
  onOpenChange,
  agentResult,
  onValidate,
  validationOptions
}: ValidationDialogProps) {
  const [selectedValue, setSelectedValue] = useState<any>(null)
  const [notes, setNotes] = useState('')

  React.useEffect(() => {
    if (agentResult) {
      setSelectedValue(agentResult.extracted_value)
      setNotes('')
    }
  }, [agentResult])

  const handleValidate = () => {
    onValidate(selectedValue, notes)
    onOpenChange(false)
  }

  if (!agentResult) return null

  const confidenceColor = agentResult.confidence > 0.8 ? 'text-green-600' : 
                         agentResult.confidence > 0.5 ? 'text-amber-600' : 'text-red-600'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Validate Agent Extraction
          </DialogTitle>
          <DialogDescription>
            Review and validate the extracted information from {agentResult.node_id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Agent Result Summary */}
          <div className="bg-slate-50 rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-sm">Extracted Value</h4>
              <Badge variant="outline" className={confidenceColor}>
                <Sparkles className="w-3 h-3 mr-1" />
                {Math.round(agentResult.confidence * 100)}% confidence
              </Badge>
            </div>
            <div className="text-lg font-mono bg-white rounded px-3 py-2">
              {JSON.stringify(agentResult.extracted_value)}
            </div>
            {agentResult.reasoning && (
              <div className="text-sm text-slate-600 mt-2">
                <span className="font-medium">Reasoning:</span> {agentResult.reasoning}
              </div>
            )}
          </div>

          {/* Source Highlights */}
          {agentResult.source_highlights && agentResult.source_highlights.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-semibold text-sm flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Evidence from Clinical Note
              </h4>
              <ScrollArea className="h-[200px] w-full rounded-md border p-4">
                {agentResult.source_highlights.map((highlight, idx) => (
                  <SourceHighlight key={idx} highlight={highlight} index={idx} />
                ))}
              </ScrollArea>
            </div>
          )}

          {/* Missing Information Warnings */}
          {agentResult.missing_info && agentResult.missing_info.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h4 className="font-semibold text-sm flex items-center gap-2 text-amber-800 mb-2">
                <AlertCircle className="w-4 h-4" />
                Missing Information
              </h4>
              <ul className="space-y-1 text-sm text-amber-700">
                {agentResult.missing_info.map((info, idx) => (
                  <li key={idx}>
                    • <span className="font-medium">{info.field}:</span> {info.reason}
                    {info.suggested_fallback && (
                      <div className="ml-4 text-xs mt-1">
                        Suggestion: {info.suggested_fallback}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Validation Options */}
          <div className="space-y-2">
            <Label>Select Validated Value</Label>
            {validationOptions ? (
              <RadioGroup value={selectedValue} onValueChange={setSelectedValue}>
                {validationOptions.map((option) => (
                  <div key={option.value} className="flex items-start space-x-2 py-2">
                    <RadioGroupItem value={option.value} id={option.value} />
                    <div className="grid gap-1.5 leading-none">
                      <label
                        htmlFor={option.value}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {option.label}
                      </label>
                      {option.description && (
                        <p className="text-sm text-muted-foreground">
                          {option.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </RadioGroup>
            ) : (
              <input
                type="text"
                value={selectedValue || ''}
                onChange={(e) => setSelectedValue(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
              />
            )}
          </div>

          {/* Clinical Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Clinical Notes (Optional)</Label>
            <Textarea
              id="notes"
              placeholder="Add any clinical notes or reasoning for this validation..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleValidate}
            disabled={selectedValue === null}
            className="gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            Validate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}