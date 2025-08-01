'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, CheckCircle, Info, HelpCircle } from "lucide-react"
import { DataConfidenceBadge } from '@/components/evidence/DataConfidenceBadge'
import type { ExtractionResult } from '@/types/missing-info'

interface InlineMedicationFormProps {
  extractionResult?: ExtractionResult
  onSubmit: (data: {
    steroidStatus: string
    avastinStatus: string
    notes?: string
  }) => void
  onConfirmMissing: () => void
}

export function InlineMedicationForm({
  extractionResult,
  onSubmit,
  onConfirmMissing
}: InlineMedicationFormProps) {
  const [steroidStatus, setSteroidStatus] = useState<string>(
    extractionResult?.value?.steroidStatus || 'unknown'
  )
  const [avastinStatus, setAvastinStatus] = useState<string>(
    extractionResult?.value?.avastinStatus || 'unknown'
  )
  const [notes, setNotes] = useState('')

  const handleSubmit = () => {
    onSubmit({
      steroidStatus,
      avastinStatus,
      notes
    })
  }

  const confidence = extractionResult?.confidence || 0
  const isMissing = extractionResult?.isMissing || confidence < 50

  return (
    <Card className="border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/20">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-yellow-600" />
          Medication Information Required
        </CardTitle>
        <div className="mt-2 space-y-2 text-sm text-muted-foreground">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">
              This information is critical for BT-RADS classification. Steroids and Avastin can cause 
              apparent tumor improvement that is unrelated to actual tumor response, affecting whether 
              we classify as BT-1a (true improvement) or BT-1b (medication effect).
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Show extraction attempt results */}
        {extractionResult && (
          <div className="p-3 bg-white dark:bg-gray-900 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Extraction Attempt</span>
              <DataConfidenceBadge
                confidence={confidence}
                source={extractionResult.source as 'nlp' | 'llm' | 'user' | 'manual'}
                field="Medications"
                isMissing={isMissing}
              />
            </div>
            {extractionResult.evidence && extractionResult.evidence.length > 0 && (
              <div className="text-xs text-muted-foreground space-y-1">
                <p className="font-medium">Evidence found:</p>
                {extractionResult.evidence.slice(0, 2).map((text, idx) => (
                  <p key={idx} className="pl-2 italic">"{text}"</p>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="space-y-4">
          {/* Steroid Status */}
          <div className="space-y-2">
            <Label className="text-base font-medium">Steroid Status</Label>
            <RadioGroup value={steroidStatus} onValueChange={setSteroidStatus}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="unknown" id="steroid-unknown" />
                <Label htmlFor="steroid-unknown" className="flex items-center gap-1">
                  <HelpCircle className="h-3 w-3" />
                  Unknown/Not documented
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="none" id="steroid-none" />
                <Label htmlFor="steroid-none">No steroids</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="stable" id="steroid-stable" />
                <Label htmlFor="steroid-stable">Stable dose</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="increasing" id="steroid-increasing" />
                <Label htmlFor="steroid-increasing">Increasing dose</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="decreasing" id="steroid-decreasing" />
                <Label htmlFor="steroid-decreasing">Decreasing/tapering</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="started" id="steroid-started" />
                <Label htmlFor="steroid-started">Recently started</Label>
              </div>
            </RadioGroup>
          </div>

          {/* Avastin Status */}
          <div className="space-y-2">
            <Label className="text-base font-medium">Avastin/Bevacizumab Status</Label>
            <RadioGroup value={avastinStatus} onValueChange={setAvastinStatus}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="unknown" id="avastin-unknown" />
                <Label htmlFor="avastin-unknown" className="flex items-center gap-1">
                  <HelpCircle className="h-3 w-3" />
                  Unknown/Not documented
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="none" id="avastin-none" />
                <Label htmlFor="avastin-none">Not on Avastin</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="ongoing" id="avastin-ongoing" />
                <Label htmlFor="avastin-ongoing">Ongoing treatment</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="first_treatment" id="avastin-first" />
                <Label htmlFor="avastin-first">First treatment/Recently started</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="started" id="avastin-started" />
                <Label htmlFor="avastin-started">Started (not first)</Label>
              </div>
            </RadioGroup>
          </div>

          {/* Additional Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes (optional)</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional context about medications..."
              className="min-h-[60px]"
            />
          </div>

          {/* Fallback Approach Alert */}
          {(steroidStatus === 'unknown' || avastinStatus === 'unknown') && (
            <Alert className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertDescription className="space-y-2">
                <p className="font-medium">Recommended Fallback Approach:</p>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  <li>When medication status is unknown, we'll default to BT-1b (possible medication effect)</li>
                  <li>This conservative approach avoids missing potential medication-related changes</li>
                  <li>Consider checking pharmacy records or contacting the treating physician</li>
                  <li>Document the uncertainty in the final report</li>
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button 
              onClick={handleSubmit}
              disabled={false}  // Allow submission even with unknown values
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Submit Information
            </Button>
            {(steroidStatus === 'unknown' || avastinStatus === 'unknown') && (
              <Button 
                variant="outline" 
                onClick={onConfirmMissing}
              >
                Proceed with Unknown Status
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}