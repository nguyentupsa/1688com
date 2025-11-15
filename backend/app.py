import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from models import (
    NegotiationRequest, NegotiationStartResponse, SystemStatus,
    LogEntry, NegotiationPhase
)
from state_machine import state_machine
from settings import settings

# Configure logging with UTF-8 encoding
import sys

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        import codecs
        # Only apply encoding fix if running directly (not through uvicorn)
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except (AttributeError, Exception):
        # Skip encoding fix if running through uvicorn or other server
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(settings.data_dir, 'app.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("[LIFESPAN] Application starting up...")

    # Ensure data directory exists
    os.makedirs(settings.data_dir, exist_ok=True)

    logger.info(f"[SERVER] 1688 Negotiation Agent server starting on port {settings.port}")
    logger.info(f"[SERVER] WebSocket server available at ws://localhost:{settings.port}")
    logger.info(f"[SERVER] AI configured: {bool(settings.google_api_key)}")

    yield

    # Shutdown
    logger.info("[LIFESPAN] Application shutting down...")

    # Stop any running negotiation
    if state_machine.is_running():
        await state_machine.stop_negotiation()

    # Close WebSocket connections properly
    connections_to_close = list(manager.active_connections)  # Copy list
    for connection in connections_to_close:
        try:
            if connection.application_state == WebSocketState.CONNECTED:
                await connection.close(code=1000, reason="Server shutdown")
        except Exception as e:
            logger.debug(f"[WS] Error closing connection during shutdown: {e}")
            # Force disconnect if close fails
            try:
                manager.disconnect(connection)
            except:
                pass

    # Clear connections list
    manager.active_connections.clear()

    logger.info("[SERVER] Server shutdown complete")

# FastAPI app
app = FastAPI(
    title="1688 Negotiation Agent",
    description="Automated B2B negotiation system for 1688.com suppliers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WS] Client connected. Total connections: {len(self.active_connections)}")

        # Warn if multiple connections detected
        if len(self.active_connections) > 1:
            logger.warning(f"[WS] ⚠️  Multiple WebSocket connections detected: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        # Make it idempotent - safe if already removed
        try:
            self.active_connections.remove(websocket)
            logger.info(f"[WS] Client disconnected. Total connections: {len(self.active_connections)}")
        except ValueError:
            logger.debug("[WS] Connection already removed or never added")
            pass  # already removed / never added

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            # Check connection state before sending
            if websocket.application_state != WebSocketState.CONNECTED:
                self.disconnect(websocket)
                return
            await websocket.send_text(message)
        except Exception as e:
            logger.warning(f"[WS] Failed to send personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        stale = []
        for ws in list(self.active_connections):  # Copy to avoid modification during iteration
            try:
                # Check connection state before sending
                if ws.application_state != WebSocketState.CONNECTED:
                    stale.append(ws)
                    continue
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"[WS] Failed to send to connection, marking as stale: {e}")
                stale.append(ws)

        # Remove stale connections safely
        for ws in stale:
            self.disconnect(ws)

manager = ConnectionManager()

# Custom logger handler to broadcast logs via WebSocket
class WebSocketLogHandler(logging.Handler):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def emit(self, record):
        try:
            # Format log message
            log_entry = self.format(record)

            # Broadcast to all WebSocket clients
            asyncio.create_task(self.manager.broadcast(log_entry))
        except Exception:
            pass

# Add WebSocket handler to root logger
ws_handler = WebSocketLogHandler(manager)
ws_handler.setFormatter(logging.Formatter('[NEGOTIATE] [%(levelname)s] %(message)s'))
logging.getLogger().addHandler(ws_handler)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/status")
async def get_status() -> SystemStatus:
    """Get system status."""
    from ai_client import ai_client

    ai_status = ai_client.get_status()
    ai_model = ai_status["model_name"]

    if not ai_status["is_available"]:
        ai_model = f"mock-enhanced ({ai_status['init_error'] or 'No valid API key'})"

    return SystemStatus(
        status="running",
        server="1688 Negotiation Agent",
        version="1.0.0",
        has_ai_api=ai_status["is_available"],
        ai_model=ai_model,
        active_sessions=1 if state_machine.is_running() else 0
    )

@app.get("/api/ai-status")
async def get_ai_status():
    """Get detailed AI client status."""
    from ai_client import ai_client

    ai_status = ai_client.get_status()
    return {
        "ai_enabled": ai_status["is_available"],
        "using_mock": ai_status["using_mock"],
        "api_key_configured": ai_status["api_key_configured"],
        "model_name": ai_status["model_name"],
        "init_error": ai_status["init_error"],
        "message": "AI Mode: Using intelligent mock responses" if ai_status["using_mock"] else "AI Mode: Google AI API is active"
    }

@app.post("/api/negotiate/start")
async def start_negotiation(request: NegotiationRequest) -> NegotiationStartResponse:
    """Start a new negotiation session."""
    try:
        if state_machine.is_running():
            current_state_value = getattr(state_machine.current_session, "current_state", None)
            return NegotiationStartResponse(
                ok=False,
                message="Another negotiation is already in progress",
                current_state=current_state_value
            )

        logger.info(f"[API] 🚀 Starting negotiation for {request.product_url}")

        # Start negotiation in background
        # Start negotiation (state_machine exposes `start(...)`)
 # Robust extract fields from model (handle different naming)
        payload = request.dict() if hasattr(request, "dict") else {}
        product_url = payload.get("product_url") or getattr(request, "product_url", None)
        if not product_url:
            raise HTTPException(status_code=400, detail="product_url is required")

        opener_text = (
            payload.get("opener_text")
            or payload.get("opener")
            or payload.get("message")
            or payload.get("opening_message")
            or getattr(request, "opener_text", None)
            or getattr(request, "opener", None)
            or getattr(request, "message", None)
            or getattr(request, "opening_message", None)
        )
        if not opener_text:
            # sensible default if FE didn't provide one
            opener_text = "你好，我对这款产品感兴趣。请问最小起订量、单价、运费和交货期是多少？支持定制和开增票吗？谢谢！"

        max_turns = payload.get("max_turns") or getattr(request, "max_turns", 6) or 6

        # Extract additional parameters like style
        style = payload.get("style") or getattr(request, "style", "Aggressive")

        logger.info(f"[API] 🚀 Starting negotiation for {product_url} with style: {style}")

        # Start negotiation (this is the real API)
        result = await state_machine.start(product_url, opener_text, int(max_turns), style)
        return NegotiationStartResponse(
            ok=True,
            session_id=getattr(state_machine.current_session, "id", None),
            message=f"Session started: {result.get('session_id')}",
            current_state=getattr(state_machine.current_session, "current_state", None)
        )

    except Exception as e:
        logger.error(f"[API]  Error starting negotiation: {e}")
        return NegotiationStartResponse(
            ok=False,
            message=f"Failed to start negotiation: {str(e)}"
        )

@app.post("/api/negotiate/stop")
async def stop_negotiation():
    """Stop the current negotiation."""
    try:
        if not state_machine.is_running():
            return {"ok": True, "message": "No negotiation in progress"}

        await state_machine.stop_negotiation()
        logger.info("[API] Negotiation stopped by user")

        return {"ok": True, "message": "Negotiation stopped successfully"}

    except Exception as e:
        logger.error(f"[API]  Error stopping negotiation: {e}")
        return {"ok": False, "message": f"Failed to stop negotiation: {str(e)}"}

@app.post("/api/session/login-only")
async def login_only():
    """Start login-only session that stops at Work Home."""
    try:
        if state_machine.is_running():
            return {"ok": False, "message": "Another session is already running"}

        logger.info("[API] Starting login-only session")
        result = await state_machine.start_login_only()

        return {
            "ok": True,
            "message": "Login session started successfully",
            "result": result
        }

    except Exception as e:
        logger.error(f"[API] Error starting login-only session: {e}")
        return {"ok": False, "message": f"Failed to start login session: {str(e)}"}

@app.post("/api/session/goto-product")
async def goto_product(request: Dict[str, str]):
    """Navigate to product URL with existing session."""
    try:
        if not state_machine.is_running():
            return {"ok": False, "message": "No active session"}

        product_url = request.get("product_url", "")
        if not product_url:
            raise HTTPException(status_code=400, detail="product_url is required")

        logger.info(f"[API] Navigating to product: {product_url}")
        result = await state_machine.goto_product(product_url)

        return {
            "ok": True,
            "message": "Successfully navigated to product",
            "result": result
        }

    except Exception as e:
        logger.error(f"[API] Error navigating to product: {e}")
        return {"ok": False, "message": f"Failed to navigate to product: {str(e)}"}

@app.get("/api/negotiation/status")
async def get_negotiation_status():
    """Get current negotiation status."""
    if not getattr(state_machine.current_session, "id", None):
        return {
            "active": False,
            "message": "No active negotiation"
        }

    session = state_machine.current_session
    return {
        "active": state_machine.is_running(),
        "session_id": session.id,
        "current_state": session.current_state,   # string
        "current_turn": session.turn,
        "max_turns": session.max_turns,
        "product_url": session.product_url,
        "total_turns": session.turn,             # tạm dùng turn làm tổng lượt
        "created_at": session.started_at,        # state tracks started_at/finished_at
        "started_at": session.started_at,
        "error_message": session.last_error
    }

@app.get("/api/artifacts")
async def list_artifacts():
    """List all available negotiation artifacts."""
    try:
        data_dir = settings.data_dir
        if not os.path.exists(data_dir):
            return {"sessions": []}

        sessions = []
        for item in os.listdir(data_dir):
            if item.startswith("session_") and os.path.isdir(os.path.join(data_dir, item)):
                session_path = os.path.join(data_dir, item)

                # Get session info
                transcript_path = os.path.join(session_path, "transcript.json")
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        transcript = json.load(f)

                    # Get screenshots
                    screenshots = []
                    screens_dir = os.path.join(data_dir, "screens")
                    if os.path.exists(screens_dir):
                        screenshots = [f for f in os.listdir(screens_dir) if f.endswith('.png')]

                    sessions.append({
                        "session_id": item,
                        "product_url": transcript.get("product_url"),
                        "created_at": transcript.get("created_at"),
                        "completed_at": transcript.get("completed_at"),
                        "total_turns": transcript.get("total_turns", 0),
                        "current_state": transcript.get("current_state"),
                        "success": transcript.get("current_state") == "S_DONE",
                        "screenshots": screenshots,
                        "has_transcript": True,
                        "has_summary": os.path.exists(os.path.join(session_path, "summary.json"))
                    })

        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {"sessions": sessions}

    except Exception as e:
        logger.error(f"[API]  Error listing artifacts: {e}")
        return {"sessions": []}

@app.post("/api/generate-opener")
async def generate_opening_message(request: Dict[str, str]):
    """Generate AI-powered opening message for negotiation."""
    try:
        product_url = request.get("product_url", "")
        if not product_url:
            raise HTTPException(status_code=400, detail="product_url is required")

        logger.info(f"[API] Generating opener for: {product_url}")

        # For now, return a template-based response
        # In a full implementation, this could scrape the product page for context
        templates = [
            "你好，我对这款产品感兴趣。请问最小起订量、单价（含税/不含税）、运费、交货期是多少？支持定制和开增票吗？谢谢！",
            "您好，我想了解这款产品的详细信息。请问：1. 最小起订量 2. 批发价格 3. 生产周期 4. 是否支持OEM定制？期待您的回复！",
            "你好，我们是采购公司，对贵司产品感兴趣。请提供产品目录、价格表、最小订单量和交货时间。谢谢！",
            "您好，请问这款产品的样品价格和大货价格分别是多少？最小起订量多少？交货期多久？",
            "你好，我司长期采购此类产品，请告知最优价格、MOQ、交期及是否支持定制。谢谢！"
        ]

        opener = templates[hash(product_url) % len(templates)]

        return {
            "ok": True,
            "text": opener.encode('utf-8').decode('utf-8'),
            "is_mock": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API]  Error generating opener: {e}")
        return {
            "ok": False,
            "text": "你好，我想了解这款产品的价格和起订量信息。",
            "is_mock": True
        }

@app.post("/api/gate/open")
async def api_gate_open(name: str = Query(..., min_length=3)):
    from state_machine import open_gate
    open_gate(name)
    return {"ok": True, "gate": name}

@app.post("/api/gate/reset")
async def api_gate_reset(name: str = Query(..., min_length=3)):
    from state_machine import reset_gate
    reset_gate(name)
    return {"ok": True, "gate": name}

@app.get("/api/artifacts/{session_id}")
async def get_session_artifacts(session_id: str):
    """Get detailed artifacts for a specific session."""
    try:
        session_path = os.path.join(settings.data_dir, session_id)
        if not os.path.exists(session_path):
            raise HTTPException(status_code=404, detail="Session not found")

        artifacts = {}

        # Transcript
        transcript_path = os.path.join(session_path, "transcript.json")
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r', encoding='utf-8') as f:
                artifacts["transcript"] = json.load(f)

        # Summary
        summary_path = os.path.join(session_path, "summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                artifacts["summary"] = json.load(f)

        # Screenshots
        screenshots = []
        screens_dir = os.path.join(settings.data_dir, "screens")
        if os.path.exists(screens_dir):
            screenshots = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
        artifacts["screenshots"] = screenshots

        return artifacts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API]  Error getting session artifacts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get artifacts: {str(e)}")

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await manager.connect(websocket)
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Connected to negotiation server",
            "timestamp": datetime.now().isoformat()
        }))

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client message with timeout to avoid hanging
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Parse client message
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                    elif message.get("type") == "stop":
                        if state_machine.is_running():
                            await state_machine.stop_negotiation()
                            await websocket.send_text(json.dumps({
                                "type": "status",
                                "message": "Negotiation stopped by user",
                                "timestamp": datetime.now().isoformat()
                            }))
                except json.JSONDecodeError:
                    # Not JSON, ignore
                    pass

            except asyncio.TimeoutError:
                # Send periodic ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    }))
                except Exception:
                    break
            except WebSocketDisconnect:
                logger.info("[WS] Client disconnected cleanly")
                break
            except Exception as e:
                logger.warning(f"[WS] Error handling message: {e}")
                break

    except WebSocketDisconnect:
        logger.info("[WS] WebSocket disconnected during handshake")
    except Exception as e:
        logger.error(f"[WS] WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

# Add CORS headers for all responses
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info"
    )