import React, { useState, useCallback, useRef } from 'react'
import { Play, Square, Sparkles, Link, Settings, Target, Clock, MessageSquare } from 'lucide-react'
import { buildApiUrl, API_PATHS } from '../config/api'

interface SystemStatus {
  status: string
  server: string
  version: string
  has_ai_api: boolean
  ai_model: string
  active_sessions: number
}

interface AIStatus {
  ai_enabled: boolean
  using_mock: boolean
  api_key_configured: boolean
  model_name: string
  init_error?: string
  message: string
}

interface ControlPanelProps {
  onStartNegotiation: (config: any) => void
  onStopNegotiation: () => void
  isRunning: boolean
  isConnected: boolean
  systemStatus?: SystemStatus | null   // optional
}


export const ControlPanel: React.FC<ControlPanelProps> = ({
  onStartNegotiation,
  onStopNegotiation,
  isRunning,
  isConnected,
  // systemStatus - removed as unused
}) => {
  const [productUrl, setProductUrl] = useState('https://detail.1688.com/offer/8213687943598.html')
  const [openingMessage, setOpeningMessage] = useState(
    '你好，我对这款产品感兴趣。请问最小起订量、单价（含税/不含税）、运费、交货期是多少？支持定制和开增票吗？谢谢！'
  )
  const [maxTurns, setMaxTurns] = useState(6)
  const [timeoutSeconds, setTimeoutSeconds] = useState(300)
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null)
  const [goals, setGoals] = useState({
    target_price: '',
    moq: '',
    lead_time: '',
    quality_requirements: '',
    samples: false,
    shipping_terms: '',
    payment_terms: ''
  })

  // Fetch AI status on component mount
  React.useEffect(() => {
    const fetchAIStatus = async () => {
      try {
        const response = await fetch(buildApiUrl(API_PATHS.AI_STATUS))
        if (response.ok) {
          const status = await response.json()
          setAiStatus(status)
        }
      } catch (error) {
        console.error('Failed to fetch AI status:', error)
      }
    }

    fetchAIStatus()
  }, [])

  // Ref to track debounced calls
  const generateOpenerTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleStart = () => {
    if (!productUrl.trim()) {
      alert('Please enter a valid 1688 product URL')
      return
    }

    if (!productUrl.includes('1688.com')) {
      alert('URL must be from 1688.com')
      return
    }

    const config = {
      product_url: productUrl.trim(),
      opening_template: openingMessage.trim() || undefined,
      goals: goals,
      max_turns: maxTurns,
      wait_timeout_s: timeoutSeconds,
      locale: 'zh'
    }

    onStartNegotiation(config)
  }

  const handleStop = () => {
    onStopNegotiation()
  }

  const loadDemoUrl = () => {
    setProductUrl('https://detail.1688.com/offer/8213687943598.html')
  }

  const generateAiOpener = useCallback(async () => {
    if (!productUrl.trim()) {
      alert('Please enter a product URL first')
      return
    }

    // Clear any existing timeout
    if (generateOpenerTimeoutRef.current) {
      clearTimeout(generateOpenerTimeoutRef.current)
    }

    // Debounce the call to prevent multiple rapid requests
    generateOpenerTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await fetch(buildApiUrl(API_PATHS.GENERATE_OPENER), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_url: productUrl }),
        })

        if (response.ok) {
          const result = await response.json()
          if (result.ok) {
            setOpeningMessage(result.text)
          }
        }
      } catch (error) {
        console.error('Failed to generate opener:', error)
        // Fallback to default message
        setOpeningMessage(
          '你好，我想了解这款产品的详细信息。请问最小起订量、单价、交货期和支持的定制服务？'
        )
      }
    }, 300) // 300ms debounce
  }, [productUrl])

  const validateUrl = (url: string) => {
    if (!url.trim()) return null
    if (!url.includes('1688.com')) {
      return 'URL must be from 1688.com'
    }
    return null
  }

  const urlError = validateUrl(productUrl)

  return (
    <div className="space-y-6">
      {/* Product Configuration */}
      <div className="card p-6 animate-in">
        <div className="flex items-center space-x-2 mb-4">
          <Link className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">Product Configuration</h3>
        </div>

        <div className="space-y-4">
          {/* Product URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              1688 Product URL
            </label>
            <div className="flex space-x-2">
              <input
                type="url"
                value={productUrl}
                onChange={(e) => setProductUrl(e.target.value)}
                placeholder="https://detail.1688.com/offer/xxxxxxxx.html"
                className={`flex-1 input ${urlError ? 'input-error' : ''}`}
                disabled={isRunning}
              />
              <button
                onClick={loadDemoUrl}
                disabled={isRunning}
                className="btn btn-outline"
                type="button"
              >
                Demo
              </button>
            </div>
            {urlError && (
              <p className="text-xs text-error-600 mt-1">{urlError}</p>
            )}
          </div>

          {/* Opening Message */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Opening Message
            </label>
            <div className="space-y-2">
              <textarea
                value={openingMessage}
                onChange={(e) => setOpeningMessage(e.target.value)}
                rows={4}
                placeholder="Enter your opening message or generate with AI..."
                className="w-full input resize-none"
                disabled={isRunning}
              />
              <button
                onClick={generateAiOpener}
                disabled={isRunning || !productUrl.trim()}
                className="btn btn-outline text-sm"
                type="button"
              >
                <Sparkles className="w-4 h-4 mr-1" />
                Generate AI Opener
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Negotiation Goals */}
      <div className="card p-6 animate-in">
        <div className="flex items-center space-x-2 mb-4">
          <Target className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">Negotiation Goals</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Price</label>
            <input
              type="text"
              value={goals.target_price}
              onChange={(e) => setGoals(prev => ({ ...prev, target_price: e.target.value }))}
              placeholder="e.g., 100 yuan/unit"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">MOQ</label>
            <input
              type="text"
              value={goals.moq}
              onChange={(e) => setGoals(prev => ({ ...prev, moq: e.target.value }))}
              placeholder="e.g., 500 pieces"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Lead Time</label>
            <input
              type="text"
              value={goals.lead_time}
              onChange={(e) => setGoals(prev => ({ ...prev, lead_time: e.target.value }))}
              placeholder="e.g., 15 days"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quality Requirements</label>
            <input
              type="text"
              value={goals.quality_requirements}
              onChange={(e) => setGoals(prev => ({ ...prev, quality_requirements: e.target.value }))}
              placeholder="e.g., ISO certified"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Shipping Terms</label>
            <input
              type="text"
              value={goals.shipping_terms}
              onChange={(e) => setGoals(prev => ({ ...prev, shipping_terms: e.target.value }))}
              placeholder="e.g., FOB Shanghai"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Terms</label>
            <input
              type="text"
              value={goals.payment_terms}
              onChange={(e) => setGoals(prev => ({ ...prev, payment_terms: e.target.value }))}
              placeholder="e.g., 30% deposit"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div className="md:col-span-2">
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={goals.samples}
                onChange={(e) => setGoals(prev => ({ ...prev, samples: e.target.checked }))}
                disabled={isRunning}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span>Request samples</span>
            </label>
          </div>
        </div>
      </div>

      {/* Negotiation Settings */}
      <div className="card p-6 animate-in">
        <div className="flex items-center space-x-2 mb-4">
          <Settings className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">Negotiation Settings</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Clock className="w-4 h-4 inline mr-1" />
              Max Turns
            </label>
            <input
              type="number"
              value={maxTurns}
              onChange={(e) => setMaxTurns(Math.max(1, Math.min(12, parseInt(e.target.value) || 1)))}
              min="1"
              max="12"
              className="input"
              disabled={isRunning}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <MessageSquare className="w-4 h-4 inline mr-1" />
              Reply Timeout (seconds)
            </label>
            <input
              type="number"
              value={timeoutSeconds}
              onChange={(e) => setTimeoutSeconds(Math.max(60, parseInt(e.target.value) || 60))}
              min="60"
              max="900"
              className="input"
              disabled={isRunning}
            />
          </div>
        </div>
      </div>

      {/* Control Buttons */}
      <div className="card p-6 animate-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={handleStart}
              disabled={isRunning || !isConnected || urlError !== null}
              className="btn btn-success text-base px-6 py-3"
            >
              <Play className="w-5 h-5 mr-2" />
              Start Negotiation
            </button>

            <button
              onClick={handleStop}
              disabled={!isRunning}
              className="btn btn-error text-base px-6 py-3"
            >
              <Square className="w-5 h-5 mr-2" />
              Stop
            </button>
          </div>

          <div className="text-sm text-gray-500">
            {isRunning ? (
              <span className="text-warning-600 font-medium">Negotiation in progress...</span>
            ) : isConnected ? (
              <span className="text-success-600 font-medium">Ready to start</span>
            ) : (
              <span className="text-error-600 font-medium">Connecting to server...</span>
            )}
          </div>
        </div>

        {aiStatus && (
          <div className={`mt-4 p-3 rounded-lg ${
            aiStatus.using_mock
              ? 'bg-warning-50 border border-warning-200'
              : 'bg-success-50 border border-success-200'
          }`}>
            <p className={`text-sm ${
              aiStatus.using_mock ? 'text-warning-800' : 'text-success-800'
            }`}>
              <strong>AI Mode:</strong> {aiStatus.message}
              {aiStatus.using_mock && aiStatus.init_error && (
                <span className="block mt-1 text-xs">
                  Reason: {aiStatus.init_error}
                </span>
              )}
            </p>
          </div>
        )}

        <div className="mt-4 text-xs text-gray-500">
          <p>• Browser will open automatically for manual login if required</p>
          <p>• All screenshots and chat logs will be saved automatically</p>
          <p>• Negotiation respects rate limits and anti-detection measures</p>
        </div>
      </div>
    </div>
  )
}