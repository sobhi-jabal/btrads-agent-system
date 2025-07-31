'use client'

import React, { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Play, 
  Pause, 
  RefreshCw, 
  Download,
  Brain,
  FileText,
  BarChart3,
  Clock
} from 'lucide-react'

import { BTRADSFlowChart } from '@/components/graph/BTRADSFlowChart'
import { ValidationDialog } from '@/components/validation/ValidationDialog'
import { ClinicalNoteViewer } from '@/components/viewer/ClinicalNoteViewer'
import { VolumeAnalysis } from '@/components/analysis/VolumeAnalysis'
import { Timeline } from '@/components/timeline/Timeline'
import { NodeDetailPanel } from '@/components/panels/NodeDetailPanel'

import { usePatientProcessor } from '@/lib/hooks/usePatientProcessor'
import { useBTRADSStore } from '@/lib/stores/btrads-store'
import { formatDate } from '@/lib/utils/date'

export default function PatientProcessingPage() {
  const params = useParams()
  const patientId = params.id as string
  
  const {
    patient,
    isProcessing,
    currentNode,
    validationPending,
    startProcessing,
    pauseProcessing,
    validateResult,
    exportResults
  } = usePatientProcessor(patientId)
  
  const { selectedNode, setSelectedNode } = useBTRADSStore()
  const [showValidation, setShowValidation] = useState(false)
  
  useEffect(() => {
    if (validationPending) {
      setShowValidation(true)
    }
  }, [validationPending])

  if (!patient) {
    return <div>Loading patient data...</div>
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Brain className="w-6 h-6" />
              BT-RADS Assessment - Patient {patientId}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Follow-up: {formatDate(patient.data.followup_date)} | 
              Baseline: {formatDate(patient.data.baseline_date)}
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <Badge variant={isProcessing ? 'default' : 'secondary'}>
              {patient.processing_status}
            </Badge>
            
            <Button
              onClick={isProcessing ? pauseProcessing : () => startProcessing()}
              disabled={patient.completed}
              variant={isProcessing ? 'destructive' : 'default'}
              size="sm"
            >
              {isProcessing ? (
                <>
                  <Pause className="w-4 h-4 mr-2" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Start Processing
                </>
              )}
            </Button>
            
            <Button
              onClick={exportResults}
              disabled={!patient.completed}
              variant="outline"
              size="sm"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Left Panel - Clinical Note */}
        <div className="w-96 border-r">
          <Tabs defaultValue="note" className="h-full flex flex-col">
            <TabsList className="w-full rounded-none border-b">
              <TabsTrigger value="note" className="flex-1">
                <FileText className="w-4 h-4 mr-2" />
                Clinical Note
              </TabsTrigger>
              <TabsTrigger value="volume" className="flex-1">
                <BarChart3 className="w-4 h-4 mr-2" />
                Volume Analysis
              </TabsTrigger>
              <TabsTrigger value="timeline" className="flex-1">
                <Clock className="w-4 h-4 mr-2" />
                Timeline
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="note" className="flex-1 p-0">
              <ClinicalNoteViewer 
                note={patient.data.clinical_note}
                highlights={currentNode?.source_highlights}
              />
            </TabsContent>
            
            <TabsContent value="volume" className="flex-1 p-4">
              <VolumeAnalysis data={patient.data} />
            </TabsContent>
            
            <TabsContent value="timeline" className="flex-1 p-4">
              <Timeline data={patient.data} />
            </TabsContent>
          </Tabs>
        </div>

        {/* Center - Graph */}
        <div className="flex-1 relative">
          <BTRADSFlowChart 
            patientId={patientId}
            onNodeClick={setSelectedNode}
          />
          
          {/* Current Processing Status */}
          {isProcessing && currentNode && (
            <Card className="absolute bottom-4 left-4 right-4 max-w-md mx-auto">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Processing Node
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-medium">{currentNode.label}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {currentNode.description}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Panel - Node Details */}
        <NodeDetailPanel
          nodeId={selectedNode}
          open={!!selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>

      {/* Validation Dialog */}
      <ValidationDialog
        open={showValidation}
        onOpenChange={setShowValidation}
        agentResult={validationPending}
        onValidate={(value, notes) => {
          validateResult(validationPending.validation_id, value, notes)
          setShowValidation(false)
        }}
        validationOptions={validationPending?.validation_options}
      />
    </div>
  )
}