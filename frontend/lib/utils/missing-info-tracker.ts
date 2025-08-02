import type { MissingInfoItem } from '@/types/missing-info'

export class MissingInfoCollector {
  private items: MissingInfoItem[] = []
  private idCounter = 0

  addMissingInfo({
    node,
    field,
    issue,
    impact,
    clinicalImpact,
    fallback,
    confidence,
    recommendation
  }: Omit<MissingInfoItem, 'id'>) {
    this.items.push({
      id: `missing-${this.idCounter++}`,
      node,
      field,
      issue,
      impact,
      clinicalImpact,
      fallback,
      confidence,
      recommendation
    })
  }

  getItems(): MissingInfoItem[] {
    return [...this.items]
  }

  getCriticalItems(): MissingInfoItem[] {
    return this.items.filter(item => item.impact === 'critical')
  }

  getFallbacksApplied(): MissingInfoItem[] {
    return this.items.filter(item => item.fallback)
  }

  getTotalCount(): number {
    return this.items.length
  }

  clear() {
    this.items = []
    this.idCounter = 0
  }

  // Helper to generate comprehensive report
  generateReport(): {
    totalMissing: number
    criticalLimitations: number
    fallbacksApplied: number
    items: MissingInfoItem[]
    summary: string
  } {
    const critical = this.getCriticalItems()
    const fallbacks = this.getFallbacksApplied()

    let summary = ''
    if (this.items.length === 0) {
      summary = 'All information available - no missing data detected'
    } else {
      summary = `${this.items.length} missing item${this.items.length !== 1 ? 's' : ''} detected`
      if (critical.length > 0) {
        summary += ` (${critical.length} critical)`
      }
      if (fallbacks.length > 0) {
        summary += ` • ${fallbacks.length} fallback${fallbacks.length !== 1 ? 's' : ''} applied`
      }
    }

    return {
      totalMissing: this.items.length,
      criticalLimitations: critical.length,
      fallbacksApplied: fallbacks.length,
      items: this.getItems(),
      summary
    }
  }
}