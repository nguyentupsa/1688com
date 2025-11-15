import React from 'react'
import { AlertCircle, Key } from 'lucide-react'

interface LoginBannerProps {
  show: boolean
}

export const LoginBanner: React.FC<LoginBannerProps> = ({ show }) => {
  if (!show) return null

  return (
    <div className="max-w-7xl mx-auto px-6 mb-6">
      <div className="bg-warning-50 border-2 border-warning-200 rounded-xl p-6 animate-in">
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-warning-200 rounded-full flex items-center justify-center">
              <Key className="w-5 h-5 text-warning-800" />
            </div>
          </div>

          <div className="flex-1">
            <h3 className="text-lg font-semibold text-warning-900 mb-2">
              Manual Login Required
            </h3>
            <div className="text-warning-800 space-y-2">
              <p className="text-sm">
                Please complete the login process in the browser window that has opened automatically.
              </p>
              <div className="bg-warning-100 rounded-lg p-3">
                <h4 className="font-medium text-warning-900 mb-1">What to do:</h4>
                <ul className="text-sm space-y-1">
                  <li>• Complete login with your 1688/Taobao credentials</li>
                  <li>• Solve any CAPTCHA or verification if prompted</li>
                  <li>• Wait for successful redirect to work.1688.com</li>
                  <li>• The system will continue automatically once logged in</li>
                </ul>
              </div>
              <div className="flex items-center space-x-1 text-xs text-warning-700">
                <AlertCircle className="w-3 h-3" />
                <span>This step is required only once per session. Login credentials are never stored.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}