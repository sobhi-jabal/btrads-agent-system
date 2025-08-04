'use client'

import React from 'react'
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Eye, EyeOff, Search } from "lucide-react"

export interface EvidenceItem {
  id: string
  sourceText: string
  matchedPattern: string
  confidence: 'high' | 'medium' | 'low'
  startIndex: number
  endIndex: number
  category: string
  alternatives?: string[]
  reasoning?: string
  relevanceScore?: number
  patternType?: string
  fullContext?: string
}

interface EvidenceHighlighterProps {
  text: string
  evidence: EvidenceItem[]
  title?: string
  showControls?: boolean
}

export function EvidenceHighlighter({ 
  text, 
  evidence, 
  title = "Clinical Note Analysis",
  showControls = true 
}: EvidenceHighlighterProps) {
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null)
  const [showAllEvidence, setShowAllEvidence] = React.useState(true)

  // Get unique categories from evidence
  const categories = React.useMemo(() => {
    const cats = Array.from(new Set(evidence.map(e => e.category)))
    return cats.sort()
  }, [evidence])

  // Color mapping for different categories and confidence levels
  const getCategoryColor = (category: string, confidence: string) => {
    const baseColors = {
      'medication': 'bg-blue-100 border-blue-300 text-blue-800',
      'radiation': 'bg-purple-100 border-purple-300 text-purple-800',
      'progression': 'bg-red-100 border-red-300 text-red-800',
      'imaging': 'bg-green-100 border-green-300 text-green-800',
      'temporal': 'bg-yellow-100 border-yellow-300 text-yellow-800',
      'clinical': 'bg-orange-100 border-orange-300 text-orange-800',
      'default': 'bg-gray-100 border-gray-300 text-gray-800'
    }
    
    const opacity = {
      'high': '',
      'medium': 'opacity-75',
      'low': 'opacity-50'
    }
    
    const color = baseColors[category as keyof typeof baseColors] || baseColors.default
    return `${color} ${opacity[confidence as keyof typeof opacity]}`
  }

  const getConfidenceIcon = (confidence: string) => {
    switch (confidence) {
      case 'high': return '✅'
      case 'medium': return '⚠️'
      case 'low': return '❓'
      default: return '●'
    }
  }

  // Create highlighted text with evidence markers
  const renderHighlightedText = () => {
    if (!text || evidence.length === 0) {
      return <p className="text-muted-foreground">{text || 'No clinical note available'}</p>
    }

    // Filter evidence based on selected category
    const filteredEvidence = selectedCategory 
      ? evidence.filter(e => e.category === selectedCategory)
      : showAllEvidence ? evidence : []

    // Sort evidence by start index to process in order
    const sortedEvidence = [...filteredEvidence].sort((a, b) => a.startIndex - b.startIndex)

    const parts = []
    let lastIndex = 0

    sortedEvidence.forEach((item, index) => {
      // Add text before this evidence
      if (item.startIndex > lastIndex) {
        parts.push(
          <span key={`text-${index}`}>
            {text.substring(lastIndex, item.startIndex)}
          </span>
        )
      }

      // Add highlighted evidence
      parts.push(
        <span
          key={`evidence-${item.id}`}
          className={`inline-block px-1 py-0.5 rounded border-2 cursor-help transition-all hover:scale-105 ${getCategoryColor(item.category, item.confidence)}`}
          title={`Pattern: ${item.matchedPattern}\nConfidence: ${item.confidence}\nCategory: ${item.category}${item.reasoning ? `\nReasoning: ${item.reasoning}` : ''}`}
        >
          <span className="text-xs mr-1">{getConfidenceIcon(item.confidence)}</span>
          {item.sourceText}
        </span>
      )

      lastIndex = item.endIndex
    })

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(
        <span key="text-end">
          {text.substring(lastIndex)}
        </span>
      )
    }

    return <div className="leading-relaxed whitespace-pre-wrap">{parts}</div>
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Search className="h-5 w-5" />
            {title}
          </CardTitle>
          {showControls && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAllEvidence(!showAllEvidence)}
              >
                {showAllEvidence ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {showAllEvidence ? 'Hide' : 'Show'} Evidence
              </Button>
            </div>
          )}
        </div>
        
        {/* Category filters */}
        {showControls && categories.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            <Button
              variant={selectedCategory === null ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All Categories
            </Button>
            {categories.map(category => (
              <Button
                key={category}
                variant={selectedCategory === category ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {category.charAt(0).toUpperCase() + category.slice(1)}
                <Badge variant="secondary" className="ml-2 text-xs">
                  {evidence.filter(e => e.category === category).length}
                </Badge>
              </Button>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent>
        {/* Clinical note with highlighting */}
        <div className="p-4 bg-muted/30 rounded-lg border min-h-[200px]">
          {renderHighlightedText()}
        </div>

        {/* Evidence summary */}
        {showAllEvidence && evidence.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="font-medium text-sm text-muted-foreground">Evidence Summary</h4>
            <div className="grid gap-2">
              {(selectedCategory ? evidence.filter(e => e.category === selectedCategory) : evidence)
                .sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0))
                .map(item => (
                <div key={item.id} className="p-3 bg-muted/20 rounded">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{getConfidenceIcon(item.confidence)}</span>
                      <span className="font-medium">{item.category}</span>
                      {item.patternType && (
                        <Badge variant="outline" className="text-xs">
                          {item.patternType}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {item.relevanceScore && (
                        <Badge variant="secondary" className="text-xs">
                          {Math.round(item.relevanceScore * 100)}% relevant
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-xs">
                        {item.confidence} confidence
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="space-y-1">
                    <div className="text-sm">
                      <span className="text-muted-foreground">Matched:</span>
                      <code className="ml-2 text-xs bg-muted px-1 rounded">{item.sourceText}</code>
                    </div>
                    
                    {item.fullContext && (
                      <div className="text-sm text-muted-foreground">
                        <span>Context:</span>
                        <span className="ml-2 italic">...{item.fullContext}...</span>
                      </div>
                    )}
                    
                    {item.reasoning && (
                      <div className="text-xs text-muted-foreground">
                        {item.reasoning}
                      </div>
                    )}
                    
                    <div className="text-xs text-muted-foreground">
                      Pattern: <code className="bg-muted px-1 rounded">{item.matchedPattern}</code>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}