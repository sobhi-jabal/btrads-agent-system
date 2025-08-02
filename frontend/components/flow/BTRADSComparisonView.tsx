import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Brain, Zap, Clock, CheckCircle, XCircle } from "lucide-react"
import type { ExtractionResult } from './ExtractionFunctions'
import { EvidenceHighlight } from './EvidenceHighlight'

interface ExtractionComparisonProps {
  results: ExtractionResult
  extractionMode: 'nlp' | 'llm' | 'both'
  clinicalNote?: string
}

export function ExtractionComparison({ results, extractionMode, clinicalNote }: ExtractionComparisonProps) {
  if (extractionMode !== 'both' || !results.nlp || !results.llm) {
    return null
  }

  const nlpMeds = results.nlp.medications
  const llmMeds = results.llm.medications
  const nlpRad = results.nlp.radiationDate
  const llmRad = results.llm.radiationDate

  return (
    <>
      <Card className="mt-4 border-2 border-primary/20">
        <CardHeader>
        <CardTitle className="text-lg">Extraction Method Comparison</CardTitle>
        <CardDescription>Compare results from NLP and LLM extraction methods</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="medications" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="medications">Medications</TabsTrigger>
            <TabsTrigger value="radiation">Radiation Date</TabsTrigger>
          </TabsList>
          
          <TabsContent value="medications" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* NLP Results */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-600" />
                  <h4 className="font-medium">NLP Pattern Matching</h4>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Steroid Status:</span>
                    <Badge variant={nlpMeds?.steroidStatus === 'none' ? 'secondary' : 'default'}>
                      {nlpMeds?.steroidStatus || 'unknown'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Avastin Status:</span>
                    <Badge variant={nlpMeds?.avastinStatus === 'none' ? 'secondary' : 'default'}>
                      {nlpMeds?.avastinStatus || 'unknown'}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Evidence: {nlpMeds?.evidence?.length || 0} patterns found
                  </div>
                </div>
              </div>

              {/* LLM Results */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-600" />
                  <h4 className="font-medium">LLM Analysis</h4>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Steroid Status:</span>
                    <Badge variant={llmMeds?.data?.steroid_status === 'none' ? 'secondary' : 'default'}>
                      {llmMeds?.data?.steroid_status || 'unknown'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Avastin Status:</span>
                    <Badge variant={llmMeds?.data?.avastin_status === 'none' ? 'secondary' : 'default'}>
                      {llmMeds?.data?.avastin_status || 'unknown'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>Confidence: {((llmMeds?.confidence || 0) * 100).toFixed(0)}%</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {(llmMeds?.processing_time || 0).toFixed(1)}s
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Agreement indicator */}
            <div className="flex items-center justify-center gap-2 pt-2 border-t">
              {nlpMeds?.steroidStatus === llmMeds?.data?.steroid_status &&
               nlpMeds?.avastinStatus === llmMeds?.data?.avastin_status ? (
                <>
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-sm text-green-600 font-medium">Methods Agree</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-orange-600" />
                  <span className="text-sm text-orange-600 font-medium">Methods Differ</span>
                </>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="radiation" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* NLP Results */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-600" />
                  <h4 className="font-medium">NLP Pattern Matching</h4>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Radiation Date:</span>
                    <Badge variant={nlpRad?.date === 'unknown' ? 'secondary' : 'default'}>
                      {nlpRad?.date || 'unknown'}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Evidence: {nlpRad?.evidence?.length || 0} patterns found
                  </div>
                </div>
              </div>

              {/* LLM Results */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-600" />
                  <h4 className="font-medium">LLM Analysis</h4>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Radiation Date:</span>
                    <Badge variant={llmRad?.data?.radiation_date === 'unknown' ? 'secondary' : 'default'}>
                      {llmRad?.data?.radiation_date || 'unknown'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>Confidence: {((llmRad?.confidence || 0) * 100).toFixed(0)}%</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {(llmRad?.processing_time || 0).toFixed(1)}s
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Agreement indicator */}
            <div className="flex items-center justify-center gap-2 pt-2 border-t">
              {nlpRad?.date === llmRad?.data?.radiation_date ? (
                <>
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-sm text-green-600 font-medium">Methods Agree</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-orange-600" />
                  <span className="text-sm text-orange-600 font-medium">Methods Differ</span>
                </>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>

    {/* Evidence Highlighting Section */}
    {clinicalNote && (
      <div className="mt-6 space-y-6">
        <Tabs defaultValue="nlp" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="nlp">NLP Evidence</TabsTrigger>
            <TabsTrigger value="llm">LLM Evidence</TabsTrigger>
          </TabsList>
          
          <TabsContent value="nlp" className="mt-4">
            {/* NLP Medication Evidence */}
            {nlpMeds?.evidence && nlpMeds.evidence.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-600" />
                  NLP Medication Extraction Evidence
                </h4>
                <EvidenceHighlight
                  clinicalNote={clinicalNote}
                  evidence={nlpMeds.evidence}
                  extractionType="medications"
                />
              </div>
            )}
            
            {/* NLP Radiation Evidence */}
            {nlpRad?.evidence && nlpRad.evidence.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-600" />
                  NLP Radiation Date Extraction Evidence
                </h4>
                <EvidenceHighlight
                  clinicalNote={clinicalNote}
                  evidence={nlpRad.evidence}
                  extractionType="radiation_date"
                />
              </div>
            )}
          </TabsContent>
          
          <TabsContent value="llm" className="mt-4">
            {/* LLM Medication Evidence */}
            {llmMeds?.evidence && llmMeds.evidence.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-600" />
                  LLM Medication Analysis Evidence
                </h4>
                <EvidenceHighlight
                  clinicalNote={clinicalNote}
                  evidence={llmMeds.evidence}
                  extractionType="medications"
                />
              </div>
            )}
            
            {/* LLM Radiation Evidence */}
            {llmRad?.evidence && llmRad.evidence.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-600" />
                  LLM Radiation Date Analysis Evidence
                </h4>
                <EvidenceHighlight
                  clinicalNote={clinicalNote}
                  evidence={llmRad.evidence}
                  extractionType="radiation_date"
                />
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    )}
    </>
  )
}