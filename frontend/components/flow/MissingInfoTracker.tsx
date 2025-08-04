import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  AlertTriangle, 
  Info, 
  CheckCircle, 
  AlertCircle, 
  ShieldAlert,
  FileWarning,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import type { MissingInfoItem } from '@/types/missing-info'

interface MissingInfoTrackerProps {
  missingItems: MissingInfoItem[]
  onResolve?: (itemId: string, value: any) => void
  className?: string
}

export const MissingInfoTracker: React.FC<MissingInfoTrackerProps> = ({
  missingItems,
  onResolve,
  className = ''
}) => {
  const [expandedItems, setExpandedItems] = React.useState<Set<string>>(new Set())

  // Categorize items
  const criticalItems = missingItems.filter(item => item.impact === 'critical')
  const highImpactItems = missingItems.filter(item => item.impact === 'high')
  const mediumImpactItems = missingItems.filter(item => item.impact === 'medium')
  const lowImpactItems = missingItems.filter(item => item.impact === 'low' || !item.impact)
  
  const fallbacksApplied = missingItems.filter(item => item.fallback)

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
      }
      return newSet
    })
  }

  if (missingItems.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            All Information Available
          </CardTitle>
          <CardDescription>
            No missing data detected in the clinical note
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileWarning className="h-5 w-5 text-orange-600" />
          Missing Information Detected
        </CardTitle>
        <CardDescription>
          {missingItems.length} item{missingItems.length !== 1 ? 's' : ''} require attention
          {fallbacksApplied.length > 0 && ` • ${fallbacksApplied.length} fallback${fallbacksApplied.length !== 1 ? 's' : ''} applied`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Statistics */}
        <div className="flex flex-wrap gap-2">
          {criticalItems.length > 0 && (
            <Badge variant="destructive">
              {criticalItems.length} Critical
            </Badge>
          )}
          {highImpactItems.length > 0 && (
            <Badge variant="default" className="bg-orange-600">
              {highImpactItems.length} High Impact
            </Badge>
          )}
          {mediumImpactItems.length > 0 && (
            <Badge variant="secondary">
              {mediumImpactItems.length} Medium Impact
            </Badge>
          )}
          {lowImpactItems.length > 0 && (
            <Badge variant="outline">
              {lowImpactItems.length} Low Impact
            </Badge>
          )}
        </div>

        {/* Critical Items */}
        {criticalItems.length > 0 && (
          <Alert variant="destructive">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Critical Limitations</AlertTitle>
            <AlertDescription className="mt-2 space-y-2">
              {criticalItems.map((item) => (
                <MissingInfoItem
                  key={item.id}
                  item={item}
                  isExpanded={expandedItems.has(item.id)}
                  onToggle={() => toggleExpanded(item.id)}
                  onResolve={onResolve}
                />
              ))}
            </AlertDescription>
          </Alert>
        )}

        {/* Other Items */}
        <div className="space-y-2">
          {[...highImpactItems, ...mediumImpactItems, ...lowImpactItems].map((item) => (
            <MissingInfoItem
              key={item.id}
              item={item}
              isExpanded={expandedItems.has(item.id)}
              onToggle={() => toggleExpanded(item.id)}
              onResolve={onResolve}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Individual missing info item component
const MissingInfoItem: React.FC<{
  item: MissingInfoItem
  isExpanded: boolean
  onToggle: () => void
  onResolve?: (itemId: string, value: any) => void
}> = ({ item, isExpanded, onToggle, onResolve }) => {
  const getIcon = () => {
    switch (item.impact) {
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-600" />
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />
      default:
        return <Info className="h-4 w-4 text-blue-600" />
    }
  }

  const getImpactColor = () => {
    switch (item.impact) {
      case 'critical':
        return 'border-red-200 bg-red-50'
      case 'high':
        return 'border-orange-200 bg-orange-50'
      case 'medium':
        return 'border-yellow-200 bg-yellow-50'
      default:
        return 'border-gray-200 bg-gray-50'
    }
  }

  return (
    <div className={`border rounded-lg p-3 ${getImpactColor()}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-2 flex-1">
          {getIcon()}
          <div className="flex-1">
            <div className="font-medium text-sm">
              NODE: {item.node?.toUpperCase() || 'UNKNOWN'}
            </div>
            <div className="text-sm text-gray-700 mt-0.5">
              {item.issue}
            </div>
            {item.confidence !== undefined && (
              <div className="text-xs text-gray-600 mt-1">
                Extraction confidence: {Math.round(item.confidence * 100)}%
              </div>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="h-6 w-6 p-0"
        >
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
      </div>

      {isExpanded && (
        <div className="mt-3 space-y-2 text-sm">
          {item.clinicalImpact && (
            <div>
              <span className="font-medium">Clinical Impact:</span>
              <span className="ml-1 text-gray-700">{item.clinicalImpact}</span>
            </div>
          )}
          
          {item.fallback && (
            <div>
              <span className="font-medium">Fallback Applied:</span>
              <span className="ml-1 text-gray-700">{item.fallback}</span>
            </div>
          )}

          {item.recommendation && (
            <div className="border-t pt-2 mt-2">
              <span className="font-medium">Recommendation:</span>
              <p className="text-gray-700 mt-1">{item.recommendation}</p>
            </div>
          )}

          {onResolve && (
            <div className="flex justify-end mt-3">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onResolve(item.id, null)}
                className="text-xs"
              >
                Provide Missing Information
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}