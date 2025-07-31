'use client'

import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  ReferenceLine
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowUp, ArrowDown, Minus, Brain, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

interface VolumeAnalysisProps {
  data: {
    baseline_flair_volume?: number | null
    followup_flair_volume?: number | null
    flair_change_percentage?: number | null
    baseline_enhancement_volume?: number | null
    followup_enhancement_volume?: number | null
    enhancement_change_percentage?: number | null
  }
}

export function VolumeAnalysis({ data }: VolumeAnalysisProps) {
  // Prepare data for charts
  const volumeData = [
    {
      name: 'FLAIR',
      baseline: data.baseline_flair_volume || 0,
      followup: data.followup_flair_volume || 0,
      change: data.flair_change_percentage || 0
    },
    {
      name: 'Enhancement',
      baseline: data.baseline_enhancement_volume || 0,
      followup: data.followup_enhancement_volume || 0,
      change: data.enhancement_change_percentage || 0
    }
  ]

  const percentageData = [
    {
      name: 'Volume Changes',
      FLAIR: data.flair_change_percentage || 0,
      Enhancement: data.enhancement_change_percentage || 0
    }
  ]

  const getChangeIcon = (change: number | null | undefined) => {
    if (!change) return <Minus className="w-4 h-4" />
    if (change > 10) return <ArrowUp className="w-4 h-4 text-red-600" />
    if (change < -10) return <ArrowDown className="w-4 h-4 text-green-600" />
    return <Minus className="w-4 h-4 text-amber-600" />
  }

  const getChangeColor = (change: number | null | undefined) => {
    if (!change) return 'text-slate-600'
    if (change > 10) return 'text-red-600'
    if (change < -10) return 'text-green-600'
    return 'text-amber-600'
  }

  const getChangeLabel = (change: number | null | undefined) => {
    if (!change) return 'No change'
    if (change > 10) return 'Increased'
    if (change < -10) return 'Decreased'
    return 'Stable'
  }

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="w-4 h-4" />
              FLAIR Volume
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Baseline</span>
                <span className="font-mono text-sm">
                  {data.baseline_flair_volume?.toFixed(1) || 'N/A'} mL
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Follow-up</span>
                <span className="font-mono text-sm">
                  {data.followup_flair_volume?.toFixed(1) || 'N/A'} mL
                </span>
              </div>
              <div className="pt-2 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Change</span>
                  <div className="flex items-center gap-2">
                    {getChangeIcon(data.flair_change_percentage)}
                    <span className={cn(
                      "font-mono text-sm font-medium",
                      getChangeColor(data.flair_change_percentage)
                    )}>
                      {data.flair_change_percentage?.toFixed(1) || '0'}%
                    </span>
                  </div>
                </div>
                <Badge 
                  variant="outline" 
                  className={cn("mt-2 w-full justify-center", getChangeColor(data.flair_change_percentage))}
                >
                  {getChangeLabel(data.flair_change_percentage)}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Enhancement Volume
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Baseline</span>
                <span className="font-mono text-sm">
                  {data.baseline_enhancement_volume?.toFixed(1) || 'N/A'} mL
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Follow-up</span>
                <span className="font-mono text-sm">
                  {data.followup_enhancement_volume?.toFixed(1) || 'N/A'} mL
                </span>
              </div>
              <div className="pt-2 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Change</span>
                  <div className="flex items-center gap-2">
                    {getChangeIcon(data.enhancement_change_percentage)}
                    <span className={cn(
                      "font-mono text-sm font-medium",
                      getChangeColor(data.enhancement_change_percentage)
                    )}>
                      {data.enhancement_change_percentage?.toFixed(1) || '0'}%
                    </span>
                  </div>
                </div>
                <Badge 
                  variant="outline" 
                  className={cn("mt-2 w-full justify-center", getChangeColor(data.enhancement_change_percentage))}
                >
                  {getChangeLabel(data.enhancement_change_percentage)}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Volume Comparison Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Volume Comparison</CardTitle>
          <CardDescription>Baseline vs Follow-up volumes in mL</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={volumeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="baseline" fill="#94a3b8" name="Baseline" />
              <Bar dataKey="followup" fill="#3b82f6" name="Follow-up" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Percentage Change Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Percentage Changes</CardTitle>
          <CardDescription>Volume changes with ±10% stability threshold</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={percentageData} margin={{ top: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <ReferenceLine y={10} stroke="#ef4444" strokeDasharray="3 3" label="10%" />
              <ReferenceLine y={-10} stroke="#10b981" strokeDasharray="3 3" label="-10%" />
              <ReferenceLine y={0} stroke="#64748b" />
              <Bar dataKey="FLAIR" fill="#8b5cf6" />
              <Bar dataKey="Enhancement" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Enhancement Priority Rule */}
      {data.flair_change_percentage && data.enhancement_change_percentage && (
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-blue-900">Enhancement Priority Rule</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-blue-800">
              When FLAIR and enhancement show opposite changes, BT-RADS prioritizes the enhancement change for overall assessment.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}