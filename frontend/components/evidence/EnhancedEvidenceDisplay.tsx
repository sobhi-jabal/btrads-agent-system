'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  ChevronDown, 
  ChevronRight, 
  FileText, 
  Target, 
  Clock,
  Sparkles,
  AlertCircle
} from "lucide-react"

interface EnhancedEvidence {
  type: string
  category: string
  text: string
  matched_text: string
  pattern: string
  pattern_type: string
  confidence: number
  start_pos: number
  end_pos: number
  context_start: number
  context_end: number
  relevance_score: number
  source_type: string
}

interface EnhancedEvidenceDisplayProps {
  evidence: EnhancedEvidence[]
  title?: string
  clinicalNote?: string
}

export function EnhancedEvidenceDisplay({ 
  evidence, 
  title = "Extraction Evidence",
  clinicalNote
}: EnhancedEvidenceDisplayProps) {
  const [expandedItems, setExpandedItems] = React.useState<Set<number>>(new Set())
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null)

  // Group evidence by category
  const groupedEvidence = React.useMemo(() => {
    const groups: Record<string, EnhancedEvidence[]> = {}
    evidence.forEach(item => {
      const category = item.category || 'general'
      if (!groups[category]) groups[category] = []
      groups[category].push(item)
    })
    return groups
  }, [evidence])

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedItems(newExpanded)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.85) return 'text-green-600 bg-green-100'
    if (confidence >= 0.7) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getRelevanceIcon = (relevance: number) => {
    if (relevance >= 0.9) return <Sparkles className="h-4 w-4 text-yellow-500" />
    if (relevance >= 0.7) return <Target className="h-4 w-4 text-blue-500" />
    return <FileText className="h-4 w-4 text-gray-500" />
  }

  const filteredEvidence = selectedCategory 
    ? evidence.filter(e => e.category === selectedCategory)
    : evidence

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{title}</span>
          <Badge variant="outline">
            {evidence.length} evidence items
          </Badge>
        </CardTitle>
        
        {/* Category filter */}
        <div className="flex gap-2 mt-3">
          <Button
            variant={selectedCategory === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Button>
          {Object.keys(groupedEvidence).map(category => (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category)}
            >
              {category}
              <Badge variant="secondary" className="ml-2">
                {groupedEvidence[category].length}
              </Badge>
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {filteredEvidence.map((item, index) => (
          <div 
            key={index}
            className="border rounded-lg p-3 hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="p-0 h-6 w-6"
                    onClick={() => toggleExpanded(index)}
                  >
                    {expandedItems.has(index) ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </Button>
                  
                  {getRelevanceIcon(item.relevance_score)}
                  
                  <code className="text-sm bg-muted px-2 py-0.5 rounded">
                    {item.matched_text}
                  </code>
                  
                  <Badge variant="outline" className="text-xs">
                    {item.pattern_type}
                  </Badge>
                  
                  <Badge className={`text-xs ${getConfidenceColor(item.confidence)}`}>
                    {(item.confidence * 100).toFixed(0)}% conf
                  </Badge>
                </div>

                {/* Collapsed view - show brief context */}
                {!expandedItems.has(index) && (
                  <p className="text-sm text-muted-foreground ml-6 line-clamp-2">
                    {item.text}
                  </p>
                )}

                {/* Expanded view - show full details */}
                {expandedItems.has(index) && (
                  <div className="ml-6 mt-2 space-y-2">
                    <div className="bg-muted/30 p-3 rounded text-sm">
                      <p className="font-medium mb-1">Full Context:</p>
                      <p className="whitespace-pre-wrap">{item.text}</p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Category:</span>
                        <Badge variant="outline" className="ml-2">{item.category}</Badge>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Type:</span>
                        <Badge variant="outline" className="ml-2">{item.type}</Badge>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Relevance:</span>
                        <span className="ml-2 font-mono">{(item.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Source:</span>
                        <span className="ml-2">{item.source_type}</span>
                      </div>
                    </div>
                    
                    <div className="text-xs text-muted-foreground">
                      <span>Position: {item.start_pos}-{item.end_pos}</span>
                      <span className="mx-2">•</span>
                      <span>Context: {item.context_start}-{item.context_end}</span>
                    </div>
                    
                    <details className="text-xs">
                      <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                        Show pattern
                      </summary>
                      <code className="block mt-1 p-2 bg-muted rounded overflow-x-auto">
                        {item.pattern}
                      </code>
                    </details>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {filteredEvidence.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="h-8 w-8 mx-auto mb-2" />
            <p>No evidence found for the selected category</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}