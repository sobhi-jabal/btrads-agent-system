'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Calendar, Zap, Camera, Clock } from 'lucide-react'
import { format, differenceInDays } from 'date-fns'
import { cn } from '@/lib/utils'

interface TimelineProps {
  data: {
    baseline_date?: Date | string
    followup_date?: Date | string
    radiation_date?: Date | string | null
  }
}

export function Timeline({ data }: TimelineProps) {
  // Parse dates
  const baseline = data.baseline_date ? new Date(data.baseline_date) : null
  const followup = data.followup_date ? new Date(data.followup_date) : null
  const radiation = data.radiation_date ? new Date(data.radiation_date) : null

  // Calculate intervals
  const daysSinceBaseline = baseline && followup 
    ? differenceInDays(followup, baseline) 
    : null
  
  const daysSinceRadiation = radiation && followup 
    ? differenceInDays(followup, radiation) 
    : null

  // Timeline events
  const events = [
    {
      date: radiation,
      label: 'Radiation Completed',
      icon: Zap,
      color: 'text-purple-600 bg-purple-100',
      description: 'XRT completion'
    },
    {
      date: baseline,
      label: 'Baseline Imaging',
      icon: Camera,
      color: 'text-blue-600 bg-blue-100',
      description: 'Initial MRI'
    },
    {
      date: followup,
      label: 'Follow-up Imaging',
      icon: Camera,
      color: 'text-green-600 bg-green-100',
      description: 'Current MRI',
      isCurrent: true
    }
  ].filter(e => e.date).sort((a, b) => a.date!.getTime() - b.date!.getTime())

  const formatDate = (date: Date | null) => {
    if (!date) return 'Not available'
    return format(date, 'MMM dd, yyyy')
  }

  return (
    <div className="space-y-4">
      {/* Key Intervals */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Days Since Radiation
            </CardTitle>
          </CardHeader>
          <CardContent>
            {daysSinceRadiation !== null ? (
              <div className="space-y-2">
                <div className="text-2xl font-bold">
                  {daysSinceRadiation} days
                </div>
                <Badge 
                  variant={daysSinceRadiation < 90 ? "destructive" : "secondary"}
                  className="w-full justify-center"
                >
                  {daysSinceRadiation < 90 ? '< 90 days' : '≥ 90 days'}
                </Badge>
                {daysSinceRadiation < 90 && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Within treatment effect window
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Radiation date not available
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Follow-up Interval
            </CardTitle>
          </CardHeader>
          <CardContent>
            {daysSinceBaseline !== null ? (
              <div className="space-y-2">
                <div className="text-2xl font-bold">
                  {daysSinceBaseline} days
                </div>
                <div className="text-xs text-muted-foreground">
                  ≈ {Math.round(daysSinceBaseline / 30)} months
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Dates not available
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Visual Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Treatment Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-border" />
            
            {/* Events */}
            <div className="space-y-6">
              {events.map((event, idx) => {
                const Icon = event.icon
                return (
                  <div key={idx} className="relative flex items-start">
                    <div className={cn(
                      "absolute left-0 w-10 h-10 rounded-full flex items-center justify-center",
                      event.color,
                      event.isCurrent && 'ring-2 ring-offset-2 ring-green-600'
                    )}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="ml-14">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-sm">{event.label}</h4>
                        {event.isCurrent && (
                          <Badge variant="outline" className="text-xs">
                            Current
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {formatDate(event.date)}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {event.description}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 90-Day Rule Reminder */}
      {daysSinceRadiation !== null && daysSinceRadiation < 90 && (
        <Card className="bg-amber-50 border-amber-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-amber-900">
              BT-RADS 90-Day Rule Active
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-amber-800">
              Patient is within 90 days of radiation completion. 
              Worsening changes are more likely to represent treatment effects (BT-3a).
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}