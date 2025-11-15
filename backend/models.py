from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class NegotiationState(str, Enum):
    ENSURE_LOGIN_VIA_TAOBAO = "S0_ENSURE_LOGIN_VIA_TAOBAO"
    OPEN_PRODUCT_AND_CHAT = "S1_OPEN_PRODUCT_AND_CHAT"
    SEND_OPENING_MESSAGE = "S2_SEND_OPENING_MESSAGE"
    WAIT_FOR_SUPPLIER_REPLY = "S3_WAIT_FOR_SUPPLIER_REPLY"
    AI_GENERATE_AND_REPLY = "S4_AI_GENERATE_AND_REPLY"
    DONE = "S_DONE"
    ERROR = "S_ERROR"

class NegotiationPhase(str, Enum):
    LOGIN = "LOGIN"
    PRODUCT = "PRODUCT"
    POPUP = "POPUP"
    CHAT = "CHAT"
    AI = "AI"
    ERROR = "ERROR"
    STATE = "STATE"
    SESSION = "SESSION"

class NegotiationGoals(BaseModel):
    target_price: Optional[str] = None
    moq: Optional[str] = None
    lead_time: Optional[str] = None
    quality_requirements: Optional[str] = None
    samples: bool = False
    shipping_terms: Optional[str] = None
    payment_terms: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user", "supplier", "assistant"
    text: str
    timestamp: datetime
    raw_html: Optional[str] = None

class NegotiationSession(BaseModel):
    id: str
    product_url: str
    opening_message: str
    goals: NegotiationGoals
    max_turns: int
    wait_timeout_s: int
    locale: str = "zh"

    # State tracking
    current_state: NegotiationState = NegotiationState.ENSURE_LOGIN_VIA_TAOBAO
    current_turn: int = 0

    # Results
    turns: List[ChatMessage] = []
    summary: Dict[str, Any] = {}

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Artifacts
    screenshots: List[str] = []
    error_message: Optional[str] = None
    evidence: Optional[str] = None

class NegotiationRequest(BaseModel):
    product_url: str
    opening_template: Optional[str] = None
    goals: NegotiationGoals = NegotiationGoals()
    max_turns: int = 6
    locale: str = "zh"
    wait_timeout_s: int = 300

class NegotiationStartResponse(BaseModel):
    ok: bool
    session_id: Optional[str] = None
    message: str
    current_state: Optional[str] = None

class SystemStatus(BaseModel):
    status: str
    server: str
    version: str
    has_ai_api: bool
    ai_model: str
    active_sessions: int = 0

class LogEntry(BaseModel):
    timestamp: datetime
    phase: NegotiationPhase
    message: str
    details: Optional[str] = None
    session_id: Optional[str] = None

class NegotiationSummary(BaseModel):
    product_url: str
    session_id: str
    total_turns: int
    price: Optional[str] = None
    moq: Optional[str] = None
    lead_time: Optional[str] = None
    notes: List[str] = []
    success: bool
    error_message: Optional[str] = None