import React from 'react'
import { Activity, Wifi, WifiOff, AlertCircle } from 'lucide-react'

interface SystemStatus {
  status: string
  server: string
  version: string
  has_ai_api: boolean
  ai_model: string
  active_sessions: number
}

interface HeaderProps {
  systemStatus: SystemStatus | null
}

export const Header: React.FC<HeaderProps> = ({ systemStatus }) => {
  const getStatusBadge = () => {
    if (!systemStatus) {
      return (
        <span className="badge badge-gray">
          <AlertCircle className="w-3 h-3 mr-1" />
          Loading...
        </span>
      )
    }

    return (
      <span className="badge badge-success">
        <Activity className="w-3 h-3 mr-1" />
        {systemStatus.status}
      </span>
    )
  }

  const getAiStatusBadge = () => {
    if (!systemStatus) {
      return <span className="badge badge-gray">AI: Checking...</span>
    }

    return (
      <span className={`badge ${systemStatus.has_ai_api ? 'badge-success' : 'badge-warning'}`}>
        AI: {systemStatus.has_ai_api ? systemStatus.ai_model : 'Mock'}
      </span>
    )
  }

  const getConnectionStatus = () => {
    // This would come from WebSocket context in a real implementation
    return true // Placeholder
  }

  return (
    <header className="bg-white border-b border-gray-200/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            {/* Logo and Title */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">1688 Negotiation Agent</h1>
                <p className="text-sm text-gray-500">Professional B2B automation platform</p>
              </div>
            </div>
          </div>

          {/* Status Badges */}
          <div className="flex items-center space-x-3">
            {getStatusBadge()}
            {getAiStatusBadge()}
            {getConnectionStatus() ? (
              <span className="badge badge-success">
                <Wifi className="w-3 h-3 mr-1" />
                Connected
              </span>
            ) : (
              <span className="badge badge-error">
                <WifiOff className="w-3 h-3 mr-1" />
                Disconnected
              </span>
            )}

            {systemStatus && systemStatus.active_sessions > 0 && (
              <span className="badge badge-primary">
                {systemStatus.active_sessions} Active
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}