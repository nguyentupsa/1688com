import React from 'react'
import { Clock, Activity, Cpu, Users, CheckCircle, AlertCircle, PlayCircle } from 'lucide-react'

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

interface StatusPanelProps {
  negotiationStatus: NegotiationStatus | null
  systemStatus: SystemStatus | null
}

export const StatusPanel: React.FC<StatusPanelProps> = ({
  negotiationStatus,
  systemStatus
}) => {
  const getStatusIcon = () => {
    if (negotiationStatus?.active) {
      return <PlayCircle className="w-5 h-5 text-warning-600 animate-pulse" />
    }
    if (negotiationStatus?.error_message) {
      return <AlertCircle className="w-5 h-5 text-error-600" />
    }
    return <CheckCircle className="w-5 h-5 text-success-600" />
  }

  const getStatusText = () => {
    if (negotiationStatus?.active) {
      return "Running"
    }
    if (negotiationStatus?.error_message) {
      return "Error"
    }
    return "Ready"
  }

  const getStatusColor = () => {
    if (negotiationStatus?.active) {
      return "text-warning-600"
    }
    if (negotiationStatus?.error_message) {
      return "text-error-600"
    }
    return "text-success-600"
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString()
  }

  const truncateUrl = (url?: string) => {
    if (!url) return '-'
    if (url.length <= 40) return url
    return url.substring(0, 37) + '...'
  }

  return (
    <div className="space-y-6">
      {/* Current Session Status */}
      <div className="card p-6 animate-in">
        <div className="flex items-center space-x-2 mb-4">
          <Activity className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">Session Status</h3>
        </div>

        <div className="space-y-4">
          {/* Status Overview */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              {getStatusIcon()}
              <span className="font-medium text-gray-900">Status:</span>
            </div>
            <span className={`font-semibold ${getStatusColor()}`}>
              {getStatusText()}
            </span>
          </div>

          {/* Session Details */}
          <div className="grid grid-cols-1 gap-3 text-sm">
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Session ID</span>
              <span className="font-mono text-gray-900">
                {negotiationStatus?.session_id || 'No active session'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Current Turn</span>
              <span className="font-semibold text-gray-900">
                {negotiationStatus?.current_turn || 0} / {negotiationStatus?.max_turns || 0}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Total Messages</span>
              <span className="font-semibold text-gray-900">
                {negotiationStatus?.total_turns || 0}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Product URL</span>
              <span className="font-mono text-xs text-gray-900 max-w-[180px] truncate" title={negotiationStatus?.product_url}>
                {truncateUrl(negotiationStatus?.product_url)}
              </span>
            </div>

            <div className="flex justify-between items-center py-2">
              <span className="text-gray-600">Current State</span>
              <span className="font-semibold text-primary-600">
                {negotiationStatus?.current_state?.replace('S', '').replace('_', ' ') || 'None'}
              </span>
            </div>
          </div>

          {/* Timestamps */}
          {(negotiationStatus?.created_at || negotiationStatus?.started_at) && (
            <div className="pt-3 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Timestamps</h4>
              <div className="space-y-1 text-xs">
                {negotiationStatus?.created_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Created:</span>
                    <span className="text-gray-700">{formatDate(negotiationStatus.created_at)}</span>
                  </div>
                )}
                {negotiationStatus?.started_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Started:</span>
                    <span className="text-gray-700">{formatDate(negotiationStatus.started_at)}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {negotiationStatus?.error_message && (
            <div className="p-3 bg-error-50 border border-error-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-1">
                <AlertCircle className="w-4 h-4 text-error-600" />
                <span className="font-medium text-error-800">Error</span>
              </div>
              <p className="text-sm text-error-700">{negotiationStatus.error_message}</p>
            </div>
          )}
        </div>
      </div>

      {/* System Information */}
      <div className="card p-6 animate-in">
        <div className="flex items-center space-x-2 mb-4">
          <Cpu className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">System Information</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 text-sm">
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Server Status</span>
              <span className="font-semibold text-success-600">
                {systemStatus?.status || 'Unknown'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Version</span>
              <span className="font-mono text-gray-900">
                {systemStatus?.version || 'Unknown'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">AI Model</span>
              <span className={`font-semibold ${
                systemStatus?.has_ai_api ? 'text-success-600' : 'text-warning-600'
              }`}>
                {systemStatus?.ai_model || 'Unknown'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2">
              <div className="flex items-center space-x-1">
                <Users className="w-4 h-4 text-gray-600" />
                <span className="text-gray-600">Active Sessions</span>
              </div>
              <span className="font-semibold text-primary-600">
                {systemStatus?.active_sessions || 0}
              </span>
            </div>
          </div>

          {/* AI Configuration Status */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Clock className="w-4 h-4 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">AI Configuration</span>
            </div>
            <p className="text-xs text-gray-600">
              {systemStatus?.has_ai_api
                ? `AI responses powered by ${systemStatus.ai_model}`
                : 'Using mock AI responses (no API key configured)'
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}