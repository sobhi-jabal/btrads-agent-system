'use client'

import React, { useCallback, useEffect, useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  NodeTypes,
  Position,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { BTRADSNode } from './BTRADSNode'
import { useBTRADSStore } from '@/lib/stores/btrads-store'
import { getBTRADSNodes, getBTRADSEdges } from '@/lib/flowchart/flowchart-config'

const nodeTypes: NodeTypes = {
  btradsNode: BTRADSNode,
}

interface BTRADSFlowChartProps {
  patientId: string
  onNodeClick?: (nodeId: string) => void
}

export function BTRADSFlowChart({ patientId, onNodeClick }: BTRADSFlowChartProps) {
  const { currentPath, activeNode, nodeStatuses } = useBTRADSStore()
  
  // Initialize nodes and edges
  const initialNodes = useMemo(() => getBTRADSNodes(), [])
  const initialEdges = useMemo(() => getBTRADSEdges(), [])
  
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Update node statuses based on processing state
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        const status = nodeStatuses[node.id] || 'pending'
        const isActive = node.id === activeNode
        const isInPath = currentPath.includes(node.id)
        
        return {
          ...node,
          data: {
            ...node.data,
            status,
            isActive,
            isInPath,
          },
        }
      })
    )
  }, [nodeStatuses, activeNode, currentPath, setNodes])

  // Update edge styling based on path
  useEffect(() => {
    setEdges((eds) =>
      eds.map((edge) => {
        const sourceIndex = currentPath.indexOf(edge.source)
        const targetIndex = currentPath.indexOf(edge.target)
        const isInPath = sourceIndex !== -1 && targetIndex !== -1 && targetIndex === sourceIndex + 1
        
        return {
          ...edge,
          animated: edge.target === activeNode,
          style: {
            ...edge.style,
            stroke: isInPath ? '#3b82f6' : '#94a3b8',
            strokeWidth: isInPath ? 3 : 2,
          },
        }
      })
    )
  }, [currentPath, activeNode, setEdges])

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id)
      }
    },
    [onNodeClick]
  )

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant={'dots' as any} gap={12} size={1} />
        <Controls />
        <MiniMap 
          nodeStrokeColor={(node) => {
            const status = node.data?.status || 'pending'
            switch (status) {
              case 'completed': return '#10b981'
              case 'active': return '#3b82f6'
              case 'error': return '#ef4444'
              case 'needs-validation': return '#f59e0b'
              default: return '#94a3b8'
            }
          }}
          nodeColor={(node) => {
            const status = node.data?.status || 'pending'
            switch (status) {
              case 'completed': return '#d1fae5'
              case 'active': return '#dbeafe'
              case 'error': return '#fee2e2'
              case 'needs-validation': return '#fef3c7'
              default: return '#f1f5f9'
            }
          }}
          maskColor="rgb(50, 50, 50, 0.8)"
        />
      </ReactFlow>
    </div>
  )
}