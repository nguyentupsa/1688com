import React from 'react'
import { CheckCircle, Download, X } from 'lucide-react'
import { buildApiUrl, API_PATHS } from '../config/api'

interface CompletionBannerProps {
  show: boolean
  data?: {
    product: string
    turns: string
    price: string
    moq: string
  }
  onClose: () => void
}

export const CompletionBanner: React.FC<CompletionBannerProps> = ({ show, data, onClose }) => {
  if (!show) return null

  const handleDownloadArtifacts = () => {
    window.open(buildApiUrl(API_PATHS.ARTIFACTS), '_blank')
  }

  return (
    <div className="max-w-7xl mx-auto px-6 mb-6">
      <div className="bg-success-50 border-2 border-success-200 rounded-xl p-6 animate-in">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4 flex-1">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-success-200 rounded-full flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-success-800" />
              </div>
            </div>

            <div className="flex-1">
              <h3 className="text-lg font-semibold text-success-900 mb-2">
                Negotiation Completed Successfully! 🎉
              </h3>

              {data && (
                <div className="bg-success-100 rounded-lg p-4 mb-3">
                  <h4 className="font-medium text-success-900 mb-2">Session Summary</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-success-700 block">Product</span>
                      <span className="font-medium text-success-900 truncate" title={data.product}>
                        {data.product.length > 30 ? data.product.substring(0, 27) + '...' : data.product}
                      </span>
                    </div>
                    <div>
                      <span className="text-success-700 block">Total Turns</span>
                      <span className="font-medium text-success-900">{data.turns}</span>
                    </div>
                    <div>
                      <span className="text-success-700 block">Price</span>
                      <span className="font-medium text-success-900">{data.price}</span>
                    </div>
                    <div>
                      <span className="text-success-700 block">MOQ</span>
                      <span className="font-medium text-success-900">{data.moq}</span>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex items-center space-x-3">
                <button
                  onClick={handleDownloadArtifacts}
                  className="btn btn-success text-sm"
                >
                  <Download className="w-4 h-4 mr-1" />
                  View Artifacts
                </button>

                <button
                  onClick={onClose}
                  className="btn btn-outline text-sm"
                >
                  Dismiss
                </button>
              </div>

              <div className="mt-3 text-xs text-success-700">
                <p>• All screenshots, chat transcripts, and logs have been saved automatically</p>
                <p>• You can access all negotiation artifacts in the artifacts gallery</p>
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="flex-shrink-0 p-1 hover:bg-success-100 rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-4 h-4 text-success-600" />
          </button>
        </div>
      </div>
    </div>
  )
}