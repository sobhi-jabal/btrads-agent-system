'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, CheckCircle, Calendar, Info, HelpCircle } from "lucide-react"
import { DataConfidenceBadge } from '@/components/evidence/DataConfidenceBadge'
import type { ExtractionResult } from '@/types/missing-info'

interface InlineRadiationFormProps {
  extractionResult?: ExtractionResult
  currentDate: string
  onSubmit: (data: {
    radiationDate: string
    radiationType?: string
    notes?: string
  }) => void
  onConfirmMissing: () => void
}

export function InlineRadiationForm({
  extractionResult,
  currentDate,
  onSubmit,
  onConfirmMissing
}: InlineRadiationFormProps) {
  const [hasRadiation, setHasRadiation] = useState<string>('unknown')
  const [radiationDate, setRadiationDate] = useState<string>(
    extractionResult?.value?.date && extractionResult.value.date !== 'unknown' 
      ? extractionResult.value.date 
      : ''
  )
  const [radiationType, setRadiationType] = useState<string>('standard')
  const [notes, setNotes] = useState('')

  const handleSubmit = () => {
    if (hasRadiation === 'no') {
      onSubmit({
        radiationDate: 'no_radiation',
        radiationType,
        notes
      })
    } else if (hasRadiation === 'unknown') {
      onSubmit({
        radiationDate: 'unknown',
        radiationType: 'unknown',
        notes
      })
    } else if (radiationDate) {
      onSubmit({
        radiationDate,
        radiationType,
        notes
      })
    }
  }

  const confidence = extractionResult?.confidence || 0
  const isMissing = extractionResult?.isMissing || (confidence < 50 && extractionResult?.value?.date === 'unknown')

  // Calculate days since radiation for validation
  const daysSinceRadiation = radiationDate && radiationDate !== 'no_radiation' 
    ? Math.floor((new Date(currentDate).getTime() - new Date(radiationDate).getTime()) / (1000 * 60 * 60 * 24))
    : null

  return (
    <Card className="border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/20">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-yellow-600" />
          Radiation Treatment Information Required
        </CardTitle>
        <div className="mt-2 space-y-2 text-sm text-muted-foreground">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">
              Radiation timing is crucial for BT-RADS classification. Changes within 90 days of radiation 
              are likely treatment effects (BT-3a) rather than true progression, affecting clinical management.
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
                field="Radiation Date"
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
          {/* Has Radiation */}
          <div className="space-y-2">
            <Label className="text-base font-medium">Has the patient received radiation therapy?</Label>
            <RadioGroup value={hasRadiation} onValueChange={setHasRadiation}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="unknown" id="rad-unknown" />
                <Label htmlFor="rad-unknown" className="flex items-center gap-1">
                  <HelpCircle className="h-3 w-3" />
                  Unknown/Not documented
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="yes" id="rad-yes" />
                <Label htmlFor="rad-yes">Yes, patient has received radiation</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="no" id="rad-no" />
                <Label htmlFor="rad-no">No radiation therapy</Label>
              </div>
            </RadioGroup>
          </div>

          {/* Radiation Date Input */}
          {hasRadiation === 'yes' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="radiation-date" className="text-base font-medium">
                  Radiation Completion Date
                </Label>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <Input
                    id="radiation-date"
                    type="date"
                    value={radiationDate}
                    onChange={(e) => setRadiationDate(e.target.value)}
                    max={currentDate}
                    className="flex-1"
                  />
                </div>
                {daysSinceRadiation !== null && (
                  <p className="text-sm text-muted-foreground">
                    {daysSinceRadiation} days since radiation
                    {daysSinceRadiation < 90 && (
                      <span className="text-orange-600 font-medium">
                        {' '}(within 90-day window)
                      </span>
                    )}
                  </p>
                )}
              </div>

              {/* Radiation Type */}
              <div className="space-y-2">
                <Label className="text-base font-medium">Radiation Type</Label>
                <RadioGroup value={radiationType} onValueChange={setRadiationType}>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="standard" id="rt-standard" />
                    <Label htmlFor="rt-standard">Standard fractionation</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="srs" id="rt-srs" />
                    <Label htmlFor="rt-srs">Stereotactic radiosurgery (SRS)</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="hypofractionated" id="rt-hypo" />
                    <Label htmlFor="rt-hypo">Hypofractionated</Label>
                  </div>
                </RadioGroup>
              </div>
            </>
          )}

          {/* Additional Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes (optional)</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional context about radiation treatment..."
              className="min-h-[60px]"
            />
          </div>

          {/* Fallback Approach Alert */}
          {hasRadiation === 'unknown' && (
            <Alert className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertDescription className="space-y-2">
                <p className="font-medium">Recommended Fallback Approach:</p>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  <li>When radiation history is unknown, we'll assume distant/no radiation (&gt;90 days)</li>
                  <li>This avoids missing true progression that needs treatment</li>
                  <li>Consider checking treatment records or contacting radiation oncology</li>
                  <li>Document the uncertainty in the final report</li>
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button 
              onClick={handleSubmit}
              disabled={hasRadiation === 'yes' && !radiationDate}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Submit Information
            </Button>
            {hasRadiation === 'unknown' && (
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