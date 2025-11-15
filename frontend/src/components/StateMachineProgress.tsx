import React from 'react'
import { Check, Play, Pause, AlertCircle, Flag } from 'lucide-react'

interface StateMachineProgressProps {
  currentState?: string
  currentTurn: number
  maxTurns: number
}

interface StateStep {
  id: string
  label: string
  icon: React.ReactNode
  description: string
}

export const StateMachineProgress: React.FC<StateMachineProgressProps> = ({
  currentState,
  currentTurn,
  maxTurns
}) => {
  const states: StateStep[] = [
    {
      id: 'S0_ENSURE_LOGIN_VIA_TAOBAO',
      label: 'Login',
      icon: <Play className="w-4 h-4" />,
      description: 'Ensure login via Taobao'
    },
    {
      id: 'S1_OPEN_PRODUCT_AND_CHAT',
      label: 'Product',
      icon: <Play className="w-4 h-4" />,
      description: 'Open product and chat'
    },
    {
      id: 'S2_SEND_OPENING_MESSAGE',
      label: 'Opening',
      icon: <Play className="w-4 h-4" />,
      description: 'Send opening message'
    },
    {
      id: 'S3_WAIT_FOR_SUPPLIER_REPLY',
      label: 'Waiting',
      icon: <Pause className="w-4 h-4" />,
      description: 'Wait for supplier reply'
    },
    {
      id: 'S4_AI_GENERATE_AND_REPLY',
      label: 'AI Reply',
      icon: <Play className="w-4 h-4" />,
      description: 'AI generates and replies'
    },
    {
      id: 'S_DONE',
      label: 'Complete',
      icon: <Flag className="w-4 h-4" />,
      description: 'Negotiation complete'
    },
    {
      id: 'S_ERROR',
      label: 'Error',
      icon: <AlertCircle className="w-4 h-4" />,
      description: 'Negotiation failed'
    }
  ]

  const getStepStatus = (stateId: string): 'pending' | 'active' | 'completed' | 'error' => {
    if (currentState === stateId) return 'active'
    if (currentState === 'S_ERROR') return 'error'
    if (currentState === 'S_DONE') return 'completed'

    // Find current state index
    const currentIndex = states.findIndex(s => s.id === currentState)
    const stepIndex = states.findIndex(s => s.id === stateId)

    if (currentIndex === -1) return 'pending'
    return stepIndex < currentIndex ? 'completed' : 'pending'
  }

  
  const getStepIcon = (status: string): React.ReactNode => {
    switch (status) {
      case 'active':
        return <div className="w-4 h-4 bg-warning-600 rounded-full animate-pulse" />
      case 'completed':
        return <Check className="w-4 h-4 text-white" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-white" />
      default:
        return <div className="w-4 h-4 bg-gray-400 rounded-full" />
    }
  }

  return (
    <div className="card p-6 animate-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Negotiation Progress</h3>
          <p className="text-sm text-gray-500 mt-1">
            Real-time state machine visualization
          </p>
        </div>

        {currentTurn > 0 && (
          <div className="text-right">
            <div className="text-2xl font-bold text-primary-600">
              {currentTurn}/{maxTurns}
            </div>
            <div className="text-xs text-gray-500">Turns</div>
          </div>
        )}
      </div>

      {/* State Progress Bar */}
      <div className="space-y-4">
        <div className="flex items-center space-x-2 overflow-x-auto pb-2">
          {states.map((state, index) => {
            const status = getStepStatus(state.id)
            const isActive = status === 'active'
            const isCompleted = status === 'completed'
            const isError = status === 'error'

            return (
              <React.Fragment key={state.id}>
                <div
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-all duration-300 cursor-pointer min-w-fit ${
                    isActive
                      ? 'border-warning-300 bg-warning-50 shadow-sm'
                      : isCompleted
                      ? 'border-success-300 bg-success-50'
                      : isError
                      ? 'border-error-300 bg-error-50'
                      : 'border-gray-200 bg-white'
                  }`}
                  title={state.description}
                >
                  <div className={`flex items-center justify-center w-6 h-6 rounded-full ${
                    isActive
                      ? 'bg-warning-600'
                      : isCompleted
                      ? 'bg-success-600'
                      : isError
                      ? 'bg-error-600'
                      : 'bg-gray-400'
                  }`}>
                    {getStepIcon(status)}
                  </div>
                  <div className="flex flex-col min-w-fit">
                    <span className={`text-xs font-medium ${
                      isActive
                        ? 'text-warning-800'
                        : isCompleted
                        ? 'text-success-800'
                        : isError
                        ? 'text-error-800'
                        : 'text-gray-600'
                    }`}>
                      {state.label}
                    </span>
                    {isActive && (
                      <span className="text-xs text-warning-600">
                        Active
                      </span>
                    )}
                  </div>
                </div>

                {/* Connector Line */}
                {index < states.length - 1 && (
                  <div className={`w-8 h-0.5 flex-shrink-0 ${
                    isCompleted ? 'bg-success-300' : 'bg-gray-300'
                  }`} />
                )}
              </React.Fragment>
            )
          })}
        </div>

        {/* Current State Details */}
        {currentState && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                getStepStatus(currentState) === 'active'
                  ? 'bg-warning-500 animate-pulse'
                  : getStepStatus(currentState) === 'completed'
                  ? 'bg-success-500'
                  : 'bg-gray-400'
              }`} />
              <span className="text-sm font-medium text-gray-700">
                Current State:
              </span>
              <span className="text-sm text-gray-900">
                {states.find(s => s.id === currentState)?.label || currentState}
              </span>
            </div>

            {states.find(s => s.id === currentState)?.description && (
              <p className="text-xs text-gray-500 mt-1 ml-4">
                {states.find(s => s.id === currentState)?.description}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}