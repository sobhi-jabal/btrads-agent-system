'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  UserCheck, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Flag
} from "lucide-react"

export interface VerificationItem {
  id: string
  category: 'calculation' | 'decision' | 'interpretation' | 'evidence'
  description: string
  aiResult: any
  isVerified?: boolean
  expertOverride?: any
  notes?: string
  timestamp?: Date
  reviewer?: string
}

export interface VerificationFeedback {
  itemId: string
  isCorrect: boolean
  suggestedCorrection?: any
  notes: string
  severity: 'minor' | 'moderate' | 'major' | 'critical'
}

interface ManualVerificationPanelProps {
  items: VerificationItem[]
  onVerify?: (feedback: VerificationFeedback) => void
  onChallenge?: (itemId: string, reason: string) => void
  readonly?: boolean
}

export function ManualVerificationPanel({ 
  items, 
  onVerify,
  onChallenge,
  readonly = false
}: ManualVerificationPanelProps) {
  const [selectedItem, setSelectedItem] = React.useState<string | null>(null)
  const [feedbackNotes, setFeedbackNotes] = React.useState<Record<string, string>>({})
  const [challengeReasons, setChallengeReasons] = React.useState<Record<string, string>>({})

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'calculation': return '🧮'
      case 'decision': return '🎯'
      case 'interpretation': return '💭'
      case 'evidence': return '🔍'
      default: return '📋'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'calculation': return 'bg-blue-50 border-blue-200 text-blue-700'
      case 'decision': return 'bg-green-50 border-green-200 text-green-700'
      case 'interpretation': return 'bg-purple-50 border-purple-200 text-purple-700'
      case 'evidence': return 'bg-orange-50 border-orange-200 text-orange-700'
      default: return 'bg-gray-50 border-gray-200 text-gray-700'
    }
  }

  const getVerificationStatus = (item: VerificationItem) => {
    if (item.isVerified === true) {
      return { icon: <CheckCircle className="h-4 w-4 text-green-500" />, text: 'Verified', color: 'text-green-600' }
    } else if (item.isVerified === false) {
      return { icon: <XCircle className="h-4 w-4 text-red-500" />, text: 'Disputed', color: 'text-red-600' }
    } else {
      return { icon: <AlertTriangle className="h-4 w-4 text-yellow-500" />, text: 'Pending Review', color: 'text-yellow-600' }
    }
  }

  const handleVerify = (itemId: string, isCorrect: boolean) => {
    const feedback: VerificationFeedback = {
      itemId,
      isCorrect,
      notes: feedbackNotes[itemId] || '',
      severity: isCorrect ? 'minor' : 'moderate' // Default severity
    }
    
    if (!isCorrect && feedbackNotes[itemId]) {
      // Determine severity based on notes content
      const notes = feedbackNotes[itemId].toLowerCase()
      if (notes.includes('critical') || notes.includes('dangerous')) {
        feedback.severity = 'critical'
      } else if (notes.includes('major') || notes.includes('significant')) {
        feedback.severity = 'major'
      }
    }
    
    onVerify?.(feedback)
    setFeedbackNotes(prev => ({ ...prev, [itemId]: '' }))
  }

  const handleChallenge = (itemId: string) => {
    const reason = challengeReasons[itemId] || 'No specific reason provided'
    onChallenge?.(itemId, reason)
    setChallengeReasons(prev => ({ ...prev, [itemId]: '' }))
  }

  const formatValue = (value: any) => {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return value?.toString() || 'N/A'
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserCheck className="h-5 w-5" />
          Manual Verification
          <Badge variant="secondary" className="ml-2">
            {items.filter(i => i.isVerified === undefined).length} pending
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {items.map(item => {
          const status = getVerificationStatus(item)
          const isSelected = selectedItem === item.id
          
          return (
            <Card 
              key={item.id} 
              className={`border ${isSelected ? 'ring-2 ring-blue-500' : ''}`}
            >
              <CardHeader 
                className="cursor-pointer hover:bg-muted/30 transition-colors pb-3"
                onClick={() => setSelectedItem(isSelected ? null : item.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge 
                      variant="outline" 
                      className={`${getCategoryColor(item.category)} border text-xs`}
                    >
                      {getCategoryIcon(item.category)} {item.category}
                    </Badge>
                    <span className="font-medium">{item.description}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {status.icon}
                    <span className={`text-sm ${status.color}`}>{status.text}</span>
                  </div>
                </div>
              </CardHeader>

              {isSelected && (
                <CardContent className="pt-0 space-y-4">
                  {/* AI Result Display */}
                  <div>
                    <h4 className="font-medium text-sm mb-2">AI Analysis Result:</h4>
                    <pre className="text-xs bg-muted/50 p-3 rounded overflow-x-auto">
                      {formatValue(item.aiResult)}
                    </pre>
                  </div>

                  {/* Expert Override (if exists) */}
                  {item.expertOverride && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">Expert Override:</h4>
                      <pre className="text-xs bg-green-50 p-3 rounded border border-green-200">
                        {formatValue(item.expertOverride)}
                      </pre>
                    </div>
                  )}

                  {/* Previous Notes */}
                  {item.notes && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">Previous Notes:</h4>
                      <p className="text-sm text-muted-foreground p-2 bg-muted/30 rounded">
                        {item.notes}
                        {item.reviewer && (
                          <span className="block text-xs mt-1">
                            — {item.reviewer} {item.timestamp && `(${item.timestamp.toLocaleString()})`}
                          </span>
                        )}
                      </p>
                    </div>
                  )}

                  {!readonly && item.isVerified === undefined && (
                    <>
                      <Separator />
                      
                      {/* Verification Actions */}
                      <div className="space-y-3">
                        <h4 className="font-medium text-sm">Expert Review:</h4>
                        
                        {/* Feedback Notes */}
                        <div>
                          <label className="text-sm font-medium mb-2 block">
                            Notes/Comments:
                          </label>
                          <textarea
                            className="w-full p-2 border rounded text-sm resize-none"
                            rows={3}
                            placeholder="Add your notes, corrections, or observations..."
                            value={feedbackNotes[item.id] || ''}
                            onChange={(e) => setFeedbackNotes(prev => ({
                              ...prev,
                              [item.id]: e.target.value
                            }))}
                          />
                        </div>

                        {/* Action Buttons */}
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="default"
                            onClick={() => handleVerify(item.id, true)}
                            className="flex items-center gap-1"
                          >
                            <ThumbsUp className="h-3 w-3" />
                            Verify Correct
                          </Button>
                          
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleVerify(item.id, false)}
                            className="flex items-center gap-1"
                          >
                            <ThumbsDown className="h-3 w-3" />
                            Mark Incorrect
                          </Button>

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleChallenge(item.id)}
                            className="flex items-center gap-1"
                          >
                            <Flag className="h-3 w-3" />
                            Challenge Decision
                          </Button>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Verification Summary (for verified items) */}
                  {item.isVerified !== undefined && (
                    <div className={`p-3 rounded border ${
                      item.isVerified 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-red-50 border-red-200'
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        {item.isVerified ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="font-medium text-sm">
                          {item.isVerified ? 'Verified as Correct' : 'Marked as Incorrect'}
                        </span>
                      </div>
                      {item.notes && (
                        <p className="text-sm text-muted-foreground">
                          {item.notes}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          )
        })}

        {items.length === 0 && (
          <div className="text-center p-8 text-muted-foreground">
            <UserCheck className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No items require manual verification</p>
            <p className="text-sm">Verification items will appear here during analysis</p>
          </div>
        )}

        {/* Summary Statistics */}
        {items.length > 0 && (
          <div className="mt-6 p-4 bg-muted/30 rounded-lg">
            <h4 className="font-medium text-sm mb-3">Verification Summary:</h4>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-lg font-bold text-green-600">
                  {items.filter(i => i.isVerified === true).length}
                </div>
                <div className="text-xs text-muted-foreground">Verified</div>
              </div>
              <div>
                <div className="text-lg font-bold text-red-600">
                  {items.filter(i => i.isVerified === false).length}
                </div>
                <div className="text-xs text-muted-foreground">Disputed</div>
              </div>
              <div>
                <div className="text-lg font-bold text-yellow-600">
                  {items.filter(i => i.isVerified === undefined).length}
                </div>
                <div className="text-xs text-muted-foreground">Pending</div>
              </div>
              <div>
                <div className="text-lg font-bold">
                  {items.length > 0 ? Math.round((items.filter(i => i.isVerified === true).length / items.length) * 100) : 0}%
                </div>
                <div className="text-xs text-muted-foreground">Accuracy</div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}