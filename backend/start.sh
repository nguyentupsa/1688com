#!/usr/bin/env bash
set -e

echo "🚀 Starting 1688 Negotiation Agent with Hybrid Browser Support..."

# Start X server for internal noVNC
echo "🖥️  Starting Xvfb on DISPLAY=:99..."
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
XVFB_PID=$!

# Wait for X server to be ready
echo "⏳ Waiting for X server to be ready..."
for i in {1..15}; do
    if [ -e /tmp/.X11-unix/X99 ]; then
        echo "✅ X server is ready!"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "⚠️  X server may not be fully ready, but continuing..."
    fi
    sleep 1
done

# Start lightweight window manager
echo "🪟 Starting Fluxbox window manager..."
fluxbox >/dev/null 2>&1 &
FLUXBOX_PID=$!

# Wait a moment for window manager
sleep 2

# Start VNC server on :5901 (no password for local dev)
echo "🔗 Starting VNC server on port 5901..."
x11vnc -display :99 -forever -shared -rfbport 5901 -nopw -quiet >/dev/null 2>&1 &
VNC_PID=$!

# Wait for VNC to be ready
sleep 2

# Start noVNC (websockify) serving HTML client at :6901
echo "🌐 Starting noVNC web interface on port 6901..."
websockify --web=/usr/share/novnc/ 6901 localhost:5901 >/dev/null 2>&1 &
NOVNC_PID=$!

# Wait for noVNC to be ready
sleep 2

echo "✅ Display services ready!"
echo "   🌐 noVNC Web Viewer: http://localhost:6901"
echo "   🔗 Direct VNC: localhost:5901"
echo ""

# Function to cleanup background processes
cleanup() {
    echo "🧹 Cleaning up background processes..."
    kill $XVFB_PID $FLUXBOX_PID $VNC_PID $NOVNC_PID 2>/dev/null || true
    wait 2>/dev/null || true
    echo "✅ Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Export DISPLAY for Python processes
export DISPLAY=:99

# Run backend
echo "🤖 Starting Python backend (supports both CDP and headed modes)..."
exec uvicorn app:app --host 0.0.0.0 --port 8000