# BT-RADS Multi-Agent System Architecture

## System Overview

This system transforms the BT-RADS algorithm into a visual, interactive multi-agent system where each decision node is handled by a specialized agent. The UI presents the algorithm as a real-time graph that clinicians can monitor, validate, and interact with.

## Key Features

### 1. **Visual Graph Interface**
- **React Flow Integration**: Interactive flowchart showing the complete BT-RADS decision tree
- **Live Path Visualization**: Highlights the actual path taken for each patient in real-time
- **Node Status Indicators**: 
  - Pending (gray)
  - Active (blue, animated)
  - Completed (green)
  - Needs Validation (amber, pulsing)
  - Error (red)

### 2. **Granular Agent Architecture**
Each BT-RADS decision point has its own specialized agent:

- **PriorAssessmentAgent** (Node 1): Evaluates suitable prior availability
- **ImagingComparisonAgent** (Node 2): Analyzes volume changes with enhancement priority
- **MedicationStatusAgent**: Extracts current steroid/Avastin status
- **RadiationTimelineAgent**: Calculates days since XRT
- **ComponentAnalysisAgent** (Node 5): Determines FLAIR vs enhancement patterns
- **ExtentAnalysisAgent** (Node 6): Applies 40% threshold rule
- **ProgressionPatternAgent** (Node 7): Evaluates multi-study progression

### 3. **Source Highlighting System**
- **Sentence-Level Evidence**: Each extraction highlights the exact sentences used
- **Confidence Scoring**: Visual indicators showing extraction confidence
- **Context Display**: Shows surrounding text for verification
- **Color-Coded Relevance**: Green (high), amber (medium), red (low)

### 4. **Step-by-Step Validation**
- **Automatic Pause Points**: System pauses at each node for validation
- **Override Capability**: Clinicians can modify any extracted value
- **Clinical Notes**: Add reasoning for any changes
- **Fallback Options**: System suggests alternatives when data is missing

### 5. **Real-Time Updates**
- **WebSocket Communication**: Live updates as agents process
- **Progress Tracking**: Visual feedback for current processing state
- **Concurrent Validation**: Multiple clinicians can validate different nodes

## Technical Architecture

### Backend (FastAPI)
```
backend/
├── agents/
│   ├── base.py                 # Base agent class with LLM integration
│   ├── extraction/             # Node-specific agents
│   └── orchestration/          # Flow control
├── api/routes/
│   ├── patients.py             # Patient data management
│   ├── agents.py               # Agent execution endpoints
│   └── validation.py           # Validation endpoints
├── models/
│   ├── patient.py              # Patient data structures
│   ├── agent.py                # Agent results & validation
│   └── btrads.py               # BT-RADS specific models
└── services/
    ├── websocket_manager.py    # Real-time communication
    └── patient_processor.py    # Processing orchestration
```

### Frontend (Next.js)
```
frontend/
├── app/
│   └── patient/[id]/           # Patient processing page
├── components/
│   ├── graph/
│   │   ├── BTRADSFlowChart.tsx # Main graph visualization
│   │   └── BTRADSNode.tsx      # Custom node component
│   ├── validation/
│   │   ├── ValidationDialog.tsx # Validation interface
│   │   └── SourceHighlight.tsx  # Evidence highlighting
│   ├── viewer/
│   │   └── ClinicalNoteViewer.tsx # Note display with highlights
│   └── analysis/
│       └── VolumeAnalysis.tsx   # Volume comparison charts
└── lib/
    ├── stores/                  # Zustand state management
    ├── hooks/                   # Custom React hooks
    └── api/                     # API client
```

## Data Flow

1. **Upload Patient Data** → CSV with clinical notes and volume measurements
2. **Initialize Processing** → Create patient session and prepare context
3. **Agent Execution Loop**:
   - Activate node in graph
   - Run specialized agent
   - Highlight source evidence
   - Present for validation
   - Update graph status
   - Proceed to next node
4. **Final Result** → BT-RADS score with complete audit trail

## Key UI/UX Decisions

### Professional Medical Interface
- **Clean, Clinical Design**: Minimal colors, focus on data
- **Status-Based Coloring**: Intuitive color mapping for medical context
- **Responsive Layout**: Three-panel design (note/graph/details)

### Validation Workflow
- **Non-Intrusive**: Validation dialog doesn't block graph view
- **Evidence-First**: Always show source before asking for validation
- **Quick Actions**: One-click approve for high-confidence extractions

### Missing Data Handling
- **Clear Indicators**: Amber warnings for missing information
- **Suggested Fallbacks**: System provides conservative defaults
- **Clinical Override**: Always allow manual input

## Security & Compliance
- **Audit Trail**: Complete history of all decisions and modifications
- **Role-Based Access**: Different permissions for viewing vs. validating
- **Data Encryption**: All patient data encrypted in transit and at rest
- **HIPAA Compliance**: Designed for healthcare data requirements

## Performance Optimizations
- **Lazy Loading**: Agents load on-demand
- **Caching**: LLM responses cached for similar queries
- **Batch Processing**: Multiple patients can process concurrently
- **Progressive Rendering**: Graph updates incrementally

This architecture ensures that the BT-RADS algorithm is transparent, verifiable, and clinician-friendly while maintaining the efficiency of automated processing.