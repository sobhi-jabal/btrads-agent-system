'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { io, Socket } from 'socket.io-client'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface UseWebSocketReturn {
  sendMessage: (message: any) => void
  lastMessage: string | null
  connectionStatus: ConnectionStatus
  error: Error | null
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [error, setError] = useState<Error | null>(null)
  
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  
  const connect = useCallback(() => {
    try {
      // Close existing connection
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.close()
      }
      
      setConnectionStatus('connecting')
      setError(null)
      
      const ws = new WebSocket(url)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnectionStatus('connected')
        reconnectAttemptsRef.current = 0
      }
      
      ws.onmessage = (event) => {
        setLastMessage(event.data)
      }
      
      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError(new Error('WebSocket error'))
        setConnectionStatus('error')
      }
      
      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnectionStatus('disconnected')
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < 5) {
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            connect()
          }, timeout)
        }
      }
      
      socketRef.current = ws
    } catch (err) {
      console.error('WebSocket connection error:', err)
      setError(err as Error)
      setConnectionStatus('error')
    }
  }, [url])
  
  const sendMessage = useCallback((message: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message)
      socketRef.current.send(messageStr)
    } else {
      console.error('WebSocket is not connected')
    }
  }, [])
  
  useEffect(() => {
    connect()
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [connect])
  
  return {
    sendMessage,
    lastMessage,
    connectionStatus,
    error
  }
}