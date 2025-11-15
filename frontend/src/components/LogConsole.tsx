import React, { useState, useRef, useEffect } from 'react'
import { Download, Trash2, Search, Filter, ChevronDown, ChevronUp } from 'lucide-react'
import { useWebSocket } from '../contexts/WebSocketContext'

interface LogFilter {
  type: 'all' | 'info' | 'warning' | 'error' | 'success'
  search: string
}

export const LogConsole: React.FC = () => {
  const { logs, clearLogs } = useWebSocket()
  const [filter, setFilter] = useState<LogFilter>({ type: 'all', search: '' })
  const [isExpanded, setIsExpanded] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const logContainerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      const container = logContainerRef.current
      container.scrollTop = container.scrollHeight
    }
  }, [logs, autoScroll])

  // Filter logs based on filter criteria
  const filteredLogs = logs.filter(log => {
    const matchesType = filter.type === 'all' || log.type === filter.type
    const matchesSearch = filter.search === '' ||
      log.message.toLowerCase().includes(filter.search.toLowerCase()) ||
      log.timestamp.toLowerCase().includes(filter.search.toLowerCase())

    return matchesType && matchesSearch
  })

  const handleDownload = () => {
    const logText = logs
      .map(log => `[${log.timestamp}] ${log.type?.toUpperCase() || 'INFO'} ${log.message}`)
      .join('\n')

    const blob = new Blob([logText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `negotiation-logs-${new Date().toISOString().slice(0, 19)}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleClear = () => {
    clearLogs()
    setFilter({ type: 'all', search: '' })
  }

  const getLogTypeClass = (type?: string) => {
    switch (type) {
      case 'error':
        return 'text-red-400'
      case 'warning':
        return 'text-yellow-400'
      case 'success':
        return 'text-green-400'
      default:
        return 'text-gray-300'
    }
  }

  const getLogTypeBg = (type?: string) => {
    switch (type) {
      case 'error':
        return 'bg-red-900/20 border-red-800/30'
      case 'warning':
        return 'bg-yellow-900/20 border-yellow-800/30'
      case 'success':
        return 'bg-green-900/20 border-green-800/30'
      default:
        return 'bg-gray-900/40 border-gray-800/30'
    }
  }

  return (
    <div className="card p-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-semibold text-gray-900">Live Logs</h3>
          <span className="badge badge-primary">{filteredLogs.length}</span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Toggle Expand */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="btn btn-outline text-sm"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            disabled={logs.length === 0}
            className="btn btn-outline text-sm"
            title="Download logs"
          >
            <Download className="w-4 h-4 mr-1" />
            Download
          </button>

          {/* Clear */}
          <button
            onClick={handleClear}
            disabled={logs.length === 0}
            className="btn btn-outline text-sm"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            Clear
          </button>
        </div>
      </div>

      {/* Filters */}
      {isExpanded && (
        <div className="mb-4 space-y-3">
          {/* Type Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-600" />
            <select
              value={filter.type}
              onChange={(e) => setFilter(prev => ({ ...prev, type: e.target.value as LogFilter['type'] }))}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Logs</option>
              <option value="info">Info</option>
              <option value="warning">Warnings</option>
              <option value="error">Errors</option>
              <option value="success">Success</option>
            </select>

            {/* Search */}
            <div className="flex-1 relative">
              <Search className="w-4 h-4 text-gray-500 absolute left-2 top-2" />
              <input
                type="text"
                value={filter.search}
                onChange={(e) => setFilter(prev => ({ ...prev, search: e.target.value }))}
                placeholder="Search logs..."
                className="w-full pl-8 pr-3 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* Auto-scroll toggle */}
            <label className="flex items-center space-x-1 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>
      )}

      {/* Log Container */}
      {isExpanded && (
        <div
          ref={logContainerRef}
          className="bg-gray-900 rounded-lg border border-gray-700 p-4 h-96 overflow-auto scrollbar-thin"
        >
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              {logs.length === 0 ? 'No logs yet...' : 'No logs match current filters'}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredLogs.map((log, index) => (
                <div
                  key={index}
                  className={`log-entry p-2 rounded border-l-2 ${getLogTypeBg(log.type)} ${getLogTypeClass(log.type)}`}
                >
                  <div className="flex items-start space-x-2">
                    <span className="text-gray-500 font-mono text-xs flex-shrink-0 mt-0.5">
                      {log.timestamp}
                    </span>
                    <span className="flex-1 break-words">
                      {log.message}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summary when collapsed */}
      {!isExpanded && (
        <div className="bg-gray-50 rounded-lg p-4 text-center text-sm text-gray-600">
          {logs.length > 0 ? (
            <span>Console collapsed ({logs.length} total logs)</span>
          ) : (
            <span>No logs to display</span>
          )}
        </div>
      )}
    </div>
  )
}