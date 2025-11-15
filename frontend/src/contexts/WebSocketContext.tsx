import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react'

interface LogEntry {
  timestamp: string
  message: string
  type?: 'info' | 'warning' | 'error' | 'success'
}

interface WebSocketContextType {
  logs: LogEntry[]
  addLog: (message: string, type?: LogEntry['type']) => void
  clearLogs: () => void
  isConnected: boolean
  sendStop: () => void
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
  wsUrl: string
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children, wsUrl }) => {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<WebSocketContextType['connectionStatus']>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number>()
  const pingIntervalRef = useRef<number>()
  const isConnectingRef = useRef(false)

  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [...prev.slice(-200), { timestamp, message, type }]) // Keep last 200 logs
  }, [])

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  const sendStop = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop' }))
    }
  }, [])

  const connect = useCallback(() => {
    // Prevent multiple concurrent connections
    if (isConnectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)) {
      return
    }

    try {
      isConnectingRef.current = true
      setConnectionStatus('connecting')
      addLog('Connecting to server...', 'info')

      // Close any existing connection first
      if (wsRef.current) {
        wsRef.current.close()
      }

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        isConnectingRef.current = false
        setIsConnected(true)
        setConnectionStatus('connected')
        addLog('Connected to negotiation server', 'success')

        // Set up ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000) // Ping every 30 seconds
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'pong') {
            // Ping response, ignore
            return
          }

          if (data.type === 'status') {
            addLog(data.message, 'info')
            return
          }

          // Regular log message
          addLog(event.data, 'info')

        } catch (error) {
          // Not JSON, treat as raw log message
          addLog(event.data, 'info')
        }
      }

      ws.onclose = (event) => {
        isConnectingRef.current = false
        setIsConnected(false)
        setConnectionStatus('disconnected')

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = undefined
        }

        if (event.wasClean) {
          addLog('Connection closed cleanly', 'info')
        } else {
          addLog('Connection lost unexpectedly', 'warning')
        }

        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          addLog('Attempting to reconnect...', 'info')
          connect()
        }, 3000)
      }

      ws.onerror = (error) => {
        isConnectingRef.current = false
        setConnectionStatus('error')
        addLog('WebSocket connection error', 'error')
        console.error('WebSocket error:', error)
      }

    } catch (error) {
      isConnectingRef.current = false
      setConnectionStatus('error')
      addLog('Failed to connect to server', 'error')
      console.error('Connection error:', error)
    }
  }, [wsUrl, addLog])

  useEffect(() => {
    connect()

    return () => {
      // Cleanup on unmount
      isConnectingRef.current = false
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, [wsUrl]) // Only depend on wsUrl, not the connect function

  const value: WebSocketContextType = {
    logs,
    addLog,
    clearLogs,
    isConnected,
    sendStop,
    connectionStatus
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}