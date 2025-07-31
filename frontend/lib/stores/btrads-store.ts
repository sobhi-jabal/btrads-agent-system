import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export type NodeStatus = 'pending' | 'active' | 'completed' | 'error' | 'needs-validation'

interface BTRADSState {
  // Current processing state
  currentPath: string[]
  activeNode: string | null
  nodeStatuses: Record<string, NodeStatus>
  
  // Selected node for detail view
  selectedNode: string | null
  
  // Agent results
  agentResults: Record<string, any>
  
  // Validation queue
  validationQueue: any[]
  
  // Actions
  setActiveNode: (nodeId: string | null) => void
  setNodeStatus: (nodeId: string, status: NodeStatus) => void
  addToPath: (nodeId: string) => void
  setSelectedNode: (nodeId: string | null) => void
  setAgentResult: (nodeId: string, result: any) => void
  addToValidationQueue: (item: any) => void
  removeFromValidationQueue: (id: string) => void
  resetState: () => void
}

const initialState = {
  currentPath: [],
  activeNode: null,
  nodeStatuses: {},
  selectedNode: null,
  agentResults: {},
  validationQueue: []
}

export const useBTRADSStore = create<BTRADSState>()(
  devtools(
    (set) => ({
      ...initialState,
      
      setActiveNode: (nodeId) => 
        set((state) => ({ 
          activeNode: nodeId,
          nodeStatuses: nodeId ? {
            ...state.nodeStatuses,
            [nodeId]: 'active'
          } : state.nodeStatuses
        })),
      
      setNodeStatus: (nodeId, status) =>
        set((state) => ({
          nodeStatuses: {
            ...state.nodeStatuses,
            [nodeId]: status
          }
        })),
      
      addToPath: (nodeId) =>
        set((state) => ({
          currentPath: [...state.currentPath, nodeId]
        })),
      
      setSelectedNode: (nodeId) =>
        set({ selectedNode: nodeId }),
      
      setAgentResult: (nodeId, result) =>
        set((state) => ({
          agentResults: {
            ...state.agentResults,
            [nodeId]: result
          }
        })),
      
      addToValidationQueue: (item) =>
        set((state) => ({
          validationQueue: [...state.validationQueue, item]
        })),
      
      removeFromValidationQueue: (id) =>
        set((state) => ({
          validationQueue: state.validationQueue.filter(item => item.id !== id)
        })),
      
      resetState: () => set(initialState)
    }),
    {
      name: 'btrads-store'
    }
  )
)