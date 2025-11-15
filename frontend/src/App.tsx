import { useState, useEffect, useCallback } from 'react'
import { WebSocketProvider } from './contexts/WebSocketContext'
import { Header } from './components/Header'
import { StateMachineProgress } from './components/StateMachineProgress'
import { ControlPanel } from './components/ControlPanel'
import { StatusPanel } from './components/StatusPanel'
import { LogConsole } from './components/LogConsole'
import { LoginBanner } from './components/LoginBanner'
import { CompletionBanner } from './components/CompletionBanner'
import LiveBrowserWindow from './components/LiveBrowserWindow'
import { useWebSocket } from './contexts/WebSocketContext'
import { WS_URL, buildApiUrl, API_PATHS } from './config/api'


interface SystemStatus {
  status: string
  server: string
  version: string
  has_ai_api: boolean
  ai_model: string
  active_sessions: number
}

interface NegotiationStatus {
  active: boolean
  session_id?: string
  current_state?: string
  current_turn: number
  max_turns: number
  product_url?: string
  total_turns: number
  created_at?: string
  started_at?: string
  error_message?: string
}

function AppContent() {
  const { logs, addLog, isConnected, sendStop } = useWebSocket()
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [negotiationStatus, setNegotiationStatus] = useState<NegotiationStatus | null>(null)
  const [showLoginBanner, setShowLoginBanner] = useState(false)
  const [showCompletionBanner, setShowCompletionBanner] = useState(false)
  const [completionData, setCompletionData] = useState<any>(null)

  // Load system status on mount and periodically
  useEffect(() => {
    const loadSystemStatus = async () => {
      try {
        const response = await fetch(buildApiUrl(API_PATHS.STATUS))
        if (response.ok) {
          const status = await response.json()
          setSystemStatus(status)
        }
      } catch (error) {
        console.error('Failed to load system status:', error)
      }
    }

    loadSystemStatus()
    const interval = setInterval(loadSystemStatus, 30000) // Refresh every 30s

    return () => clearInterval(interval)
  }, [])

  // Load negotiation status
  useEffect(() => {
    const loadNegotiationStatus = async () => {
      try {
        const response = await fetch(buildApiUrl(API_PATHS.NEGOTIATION_STATUS))
        if (response.ok) {
          const status = await response.json()
          setNegotiationStatus(status)
        }
      } catch (error) {
        console.error('Failed to load negotiation status:', error)
      }
    }

    // Load initial status
    loadNegotiationStatus()

    // Set up polling for active negotiation
    const interval = setInterval(() => {
      if (negotiationStatus?.active) {
        loadNegotiationStatus()
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [negotiationStatus?.active])

  // Process logs for UI updates
  useEffect(() => {
    logs.forEach(log => {
      const logMessage = typeof log === 'string' ? log : log.message

      // Handle login banner
      if (logMessage.includes('Login UI detected - waiting for manual login')) {
        setShowLoginBanner(true)
      } else if (logMessage.includes('Manual login completed') || logMessage.includes('Already logged in')) {
        setShowLoginBanner(false)
      }

      // Handle completion
      if (logMessage.includes('SESSION COMPLETED') || logMessage.includes('Negotiation completed successfully')) {
        setShowCompletionBanner(true)
        // Extract completion data if available
        const sessionMatch = logMessage.match(/Product: (.+)/)
        const turnsMatch = logMessage.match(/Total turns: (\d+)/)
        const priceMatch = logMessage.match(/Price: (.+)/)
        const moqMatch = logMessage.match(/MOQ: (.+)/)

        setCompletionData({
          product: sessionMatch?.[1] || 'Unknown',
          turns: turnsMatch?.[1] || '0',
          price: priceMatch?.[1] || 'Not discussed',
          moq: moqMatch?.[1] || 'Not discussed'
        })
      }
    })
  }, [logs])

  const handleStartNegotiation = useCallback(async (config: any) => {
    try {
      addLog('Starting negotiation session...')
      const response = await fetch(buildApiUrl(API_PATHS.NEGOTIATE_START), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })

      if (!response.ok) {
        throw new Error('Failed to start negotiation')
      }

      const result = await response.json()
      if (result.ok) {
        addLog(`Negotiation started (Session: ${result.session_id})`)
        // Reload negotiation status
        setTimeout(() => {
          fetch(buildApiUrl(API_PATHS.NEGOTIATION_STATUS))
            .then(res => res.json())
            .then(setNegotiationStatus)
            .catch(console.error)
        }, 1000)
      } else {
        addLog(`Failed to start: ${result.message}`, 'error')
      }
    } catch (error) {
      addLog(`Error starting negotiation: ${error}`, 'error')
    }
  }, [addLog])

  const handleStopNegotiation = useCallback(async () => {
    try {
      addLog('Stopping negotiation...')
      await fetch(buildApiUrl(API_PATHS.NEGOTIATE_STOP), { method: 'POST' })
      addLog('Negotiation stopped by user')
      sendStop()
    } catch (error) {
      addLog(`Error stopping negotiation: ${error}`, 'error')
    }
  }, [addLog, sendStop])

  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <Header systemStatus={systemStatus} />

      {/* Login Banner */}
      <LoginBanner show={showLoginBanner} />

      {/* Completion Banner */}
      <CompletionBanner
        show={showCompletionBanner}
        data={completionData}
        onClose={() => setShowCompletionBanner(false)}
      />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Controls and Progress */}
          <div className="lg:col-span-2 space-y-8">
            {/* State Machine Progress */}
            <StateMachineProgress
              currentState={negotiationStatus?.current_state}
              currentTurn={negotiationStatus?.current_turn || 0}
              maxTurns={negotiationStatus?.max_turns || 6}
            />

            {/* Control Panel */}
            <ControlPanel
              onStartNegotiation={handleStartNegotiation}
              onStopNegotiation={handleStopNegotiation}
              isRunning={negotiationStatus?.active || false}
              isConnected={isConnected}
              systemStatus={systemStatus}
            />
          </div>

          {/* Right Column - Status and Info */}
          <div className="space-y-8">
            {/* Status Panel */}
            <StatusPanel
              negotiationStatus={negotiationStatus}
              systemStatus={systemStatus}
            />
          </div>
        </div>

        {/* Live Browser Window - Full Width */}
        <div className="mt-8">
          <LiveBrowserWindow title="Live 1688 Browser Session" />
        </div>

        {/* Log Console - Full Width */}
        <div className="mt-8">
          <LogConsole />
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <WebSocketProvider wsUrl={WS_URL}>
      <AppContent />
    </WebSocketProvider>
  )
}

export default App