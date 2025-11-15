/**
 * Centralized API and WebSocket configuration
 *
 * This file provides normalized base URLs for REST API and WebSocket connections
 * that work correctly in both production and development environments.
 */

// Normalize REST API base URL
// - If VITE_API_URL is set (e.g., http://localhost:8000/api), use it and remove trailing slash
// - If not set, default to <origin>/api
// - Final result should NOT include trailing slash
export const API_URL = (
  import.meta.env.VITE_API_URL || `${window.location.origin}/api`
).replace(/\/+$/, '');

// Normalize WebSocket URL
// - If VITE_WS_URL is set (e.g., ws://localhost:8000/ws/logs), use it directly
// - If not set, construct from current location: <protocol>//<host>/ws/logs
// - Final result should be the COMPLETE WebSocket URL including /ws/logs path
export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${
    window.location.host
  }/ws/logs`;

// Export paths for reference (don't append to API_URL/WS_URL)
export const API_PATHS = {
  STATUS: '/status',
  AI_STATUS: '/ai-status',
  NEGOTIATION_STATUS: '/negotiation/status',
  NEGOTIATE_START: '/negotiate/start',
  NEGOTIATE_STOP: '/negotiate/stop',
  GENERATE_OPENER: '/generate-opener',
  ARTIFACTS: '/artifacts'
} as const;

// Helper function to build API URLs
export const buildApiUrl = (path: string): string => {
  // Ensure path starts with / but doesn't double slash
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_URL}${normalizedPath}`;
};