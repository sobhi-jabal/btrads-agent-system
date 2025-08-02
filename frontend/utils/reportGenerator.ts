/**
 * Generate standalone HTML report for BT-RADS analysis
 */

import type { EvidenceItem } from '@/components/evidence/EvidenceHighlighter'

export interface BTRADSReportData {
  patientId: string
  clinicalNote: string
  btRadsScore: string
  finalDecision: string
  reasoning: string
  decisionPath: Array<{
    step: string
    decision: string
    reasoning: string
  }>
  evidence: EvidenceItem[]
  extractedData: {
    steroidStatus?: string
    avastinStatus?: string
    radiationDate?: string
    imagingAssessment?: string
  }
  timestamp: string
}

/**
 * Generate HTML string for BT-RADS report
 */
export function generateBTRADSReport(data: BTRADSReportData): string {
  const evidenceColors = {
    medication: '#3b82f6',
    temporal: '#8b5cf6',
    assessment: '#10b981',
    general: '#6b7280'
  }

  // Function to highlight evidence in text
  const highlightEvidence = (text: string, evidence: EvidenceItem[]): string => {
    if (!evidence || evidence.length === 0) return text

    // Sort evidence by start position (descending) to avoid position shifts
    const sortedEvidence = [...evidence].sort((a, b) => (b.startIndex || 0) - (a.startIndex || 0))
    
    let highlightedText = text
    sortedEvidence.forEach(item => {
      if (item.startIndex !== undefined && item.endIndex !== undefined && 
          item.startIndex >= 0 && item.endIndex > item.startIndex) {
        const before = highlightedText.substring(0, item.startIndex)
        const highlighted = highlightedText.substring(item.startIndex, item.endIndex)
        const after = highlightedText.substring(item.endIndex)
        
        const color = evidenceColors[item.category as keyof typeof evidenceColors] || evidenceColors.general
        highlightedText = before + 
          `<span style="background-color: ${color}20; border-bottom: 2px solid ${color}; padding: 2px 4px; border-radius: 3px;" title="${item.reasoning || ''}">${highlighted}</span>` + 
          after
      }
    })
    
    return highlightedText
  }

  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BT-RADS Report - ${data.patientId}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
      line-height: 1.6;
      color: #1f2937;
      background: #f9fafb;
      padding: 20px;
    }
    
    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      overflow: hidden;
    }
    
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 30px;
    }
    
    .header h1 {
      font-size: 28px;
      margin-bottom: 10px;
    }
    
    .header-info {
      display: flex;
      justify-content: space-between;
      margin-top: 20px;
      font-size: 14px;
      opacity: 0.95;
    }
    
    .section {
      padding: 30px;
      border-bottom: 1px solid #e5e7eb;
    }
    
    .section:last-child {
      border-bottom: none;
    }
    
    .section-title {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 20px;
      color: #4b5563;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    
    .score-badge {
      display: inline-block;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 18px;
      font-weight: bold;
      margin-bottom: 10px;
    }
    
    .score-bt-0 { background: #fee2e2; color: #dc2626; }
    .score-bt-1a { background: #dcfce7; color: #16a34a; }
    .score-bt-1b { background: #dbeafe; color: #2563eb; }
    .score-bt-2 { background: #fef3c7; color: #d97706; }
    .score-bt-3a { background: #fde68a; color: #f59e0b; }
    .score-bt-3b { background: #fed7aa; color: #ea580c; }
    .score-bt-3c { background: #fecaca; color: #ef4444; }
    .score-bt-4 { background: #e0e7ff; color: #6366f1; }
    
    .extracted-data {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 15px;
      margin-bottom: 20px;
    }
    
    .data-card {
      padding: 15px;
      border-radius: 6px;
      background: #f3f4f6;
    }
    
    .data-label {
      font-size: 12px;
      color: #6b7280;
      text-transform: uppercase;
      margin-bottom: 5px;
    }
    
    .data-value {
      font-size: 16px;
      font-weight: 600;
      color: #1f2937;
    }
    
    .clinical-note {
      background: #f9fafb;
      padding: 20px;
      border-radius: 6px;
      font-family: 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.8;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
    
    .decision-path {
      display: flex;
      flex-direction: column;
      gap: 15px;
    }
    
    .decision-step {
      display: flex;
      align-items: flex-start;
      gap: 15px;
    }
    
    .step-number {
      flex-shrink: 0;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: #6366f1;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
    }
    
    .step-content {
      flex: 1;
      padding-bottom: 15px;
      border-left: 2px solid #e5e7eb;
      padding-left: 20px;
      margin-left: 15px;
    }
    
    .decision-step:last-child .step-content {
      border-left: none;
    }
    
    .step-title {
      font-weight: 600;
      margin-bottom: 5px;
    }
    
    .step-decision {
      color: #059669;
      font-weight: 500;
      margin-bottom: 5px;
    }
    
    .step-reasoning {
      color: #6b7280;
      font-size: 14px;
    }
    
    .legend {
      display: flex;
      gap: 20px;
      margin-top: 15px;
      font-size: 12px;
    }
    
    .legend-item {
      display: flex;
      align-items: center;
      gap: 5px;
    }
    
    .legend-color {
      width: 20px;
      height: 12px;
      border-radius: 2px;
    }
    
    .footer {
      padding: 20px 30px;
      background: #f9fafb;
      text-align: center;
      color: #6b7280;
      font-size: 12px;
    }
    
    @media print {
      body {
        background: white;
        padding: 0;
      }
      
      .container {
        box-shadow: none;
      }
      
      .header {
        background: #4b5563;
        print-color-adjust: exact;
        -webkit-print-color-adjust: exact;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>BT-RADS Analysis Report</h1>
      <div class="header-info">
        <div>
          <strong>Patient ID:</strong> ${data.patientId}
        </div>
        <div>
          <strong>Generated:</strong> ${new Date(data.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
    
    <div class="section">
      <h2 class="section-title">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" fill="#6b7280"/>
          <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 100 4h1a3 3 0 013 3v1a1 1 0 11-2 0v-1a1 1 0 00-1-1H6a4 4 0 01-2-7.48V5z" fill="#6b7280"/>
        </svg>
        Final BT-RADS Classification
      </h2>
      <div class="score-badge score-bt-${data.btRadsScore.toLowerCase().replace(/[^a-z0-9]/g, '-')}">
        ${data.btRadsScore}
      </div>
      <p><strong>Decision:</strong> ${data.finalDecision}</p>
      <p style="margin-top: 10px; color: #6b7280;">${data.reasoning}</p>
    </div>
    
    <div class="section">
      <h2 class="section-title">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M9 4.5a.75.75 0 01.75.75v4.25h4.25a.75.75 0 010 1.5h-4.25v4.25a.75.75 0 01-1.5 0V11H4a.75.75 0 010-1.5h4.25V5.25A.75.75 0 019 4.5z" fill="#6b7280"/>
        </svg>
        Extracted Clinical Data
      </h2>
      <div class="extracted-data">
        ${data.extractedData.steroidStatus ? `
        <div class="data-card">
          <div class="data-label">Steroid Status</div>
          <div class="data-value">${data.extractedData.steroidStatus}</div>
        </div>` : ''}
        ${data.extractedData.avastinStatus ? `
        <div class="data-card">
          <div class="data-label">Avastin Status</div>
          <div class="data-value">${data.extractedData.avastinStatus}</div>
        </div>` : ''}
        ${data.extractedData.radiationDate ? `
        <div class="data-card">
          <div class="data-label">Radiation Date</div>
          <div class="data-value">${data.extractedData.radiationDate}</div>
        </div>` : ''}
        ${data.extractedData.imagingAssessment ? `
        <div class="data-card">
          <div class="data-label">Imaging Assessment</div>
          <div class="data-value">${data.extractedData.imagingAssessment}</div>
        </div>` : ''}
      </div>
    </div>
    
    <div class="section">
      <h2 class="section-title">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" fill="#6b7280"/>
          <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" fill="#6b7280"/>
        </svg>
        Clinical Note with Evidence
      </h2>
      <div class="clinical-note">
        ${highlightEvidence(data.clinicalNote, data.evidence)}
      </div>
      <div class="legend">
        <div class="legend-item">
          <div class="legend-color" style="background: ${evidenceColors.medication}20; border: 1px solid ${evidenceColors.medication};"></div>
          <span>Medications</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: ${evidenceColors.temporal}20; border: 1px solid ${evidenceColors.temporal};"></div>
          <span>Temporal</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: ${evidenceColors.assessment}20; border: 1px solid ${evidenceColors.assessment};"></div>
          <span>Assessment</span>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h2 class="section-title">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" fill="#6b7280"/>
        </svg>
        Decision Path
      </h2>
      <div class="decision-path">
        ${data.decisionPath.map((step, index) => `
        <div class="decision-step">
          <div class="step-number">${index + 1}</div>
          <div class="step-content">
            <div class="step-title">${step.step}</div>
            <div class="step-decision">→ ${step.decision}</div>
            <div class="step-reasoning">${step.reasoning}</div>
          </div>
        </div>
        `).join('')}
      </div>
    </div>
    
    <div class="footer">
      <p>This report was generated by the BT-RADS Agent System</p>
      <p>For clinical use only • Please verify all findings</p>
    </div>
  </div>
</body>
</html>
  `.trim()

  return html
}

/**
 * Download HTML report as file
 */
export function downloadBTRADSReport(data: BTRADSReportData, filename?: string) {
  const html = generateBTRADSReport(data)
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `btrads-report-${data.patientId}-${Date.now()}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}