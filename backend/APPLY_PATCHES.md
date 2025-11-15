# 1688 Negotiation Agent Refactor Instructions

## Apply Patches

```bash
# Navigate to backend directory
cd backend

# Apply all patches
patch -p1 < playwright_driver_refactor.patch
patch -p1 < state_machine_refactor.patch
patch -p1 < app_refactor.patch
```

## Manual Gate Control

### API Endpoints

**Open Gates (continue to next step):**
```bash
curl -X POST "http://localhost:8000/api/gate/open?name=CONFIRM_AFTER_LOGIN"
curl -X POST "http://localhost:8000/api/gate/open?name=CONFIRM_PRODUCT_AND_CHAT"
curl -X POST "http://localhost:8000/api/gate/open?name=CONFIRM_AFTER_SEND"
```

**Reset Gates (if needed):**
```bash
curl -X POST "http://localhost:8000/api/gate/reset?name=<gate_name>"
```

### Gate Timeouts (Auto-proceed)

- `CONFIRM_AFTER_LOGIN`: 20 seconds
- `CONFIRM_PRODUCT_AND_CHAT`: 20 seconds
- `CONFIRM_AFTER_SEND`: 20 seconds

If no manual gate opening, system auto-proceeds after timeout.

## Key Improvements

✅ **Stable Login Flow**
- Detects login modal visibility
- Waits for stable 1.5s after modal disappears
- No navigation while modal visible
- Comprehensive logging

✅ **Chat Readiness**
- Waits for chat input to be truly visible
- Checks both main page and iframes
- Timeout protection

✅ **Event-Driven Gates**
- Manual control via API
- Auto-timeout fallback
- Clear state transitions

✅ **Noise Filtering**
- Filters console noise (gyroscope, APLUS, etc.)
- Clean log output

✅ **Error Handling**
- Detailed error logging with stack traces
- Graceful degradation
- Resource cleanup

## Log Patterns

Watch for these log patterns:
- `[STATE]` - State machine transitions
- `[LOGIN]` - Login process events
- `[CHAT]` - Chat-related events
- `[GATE]` - Gate operations
- `[API]` - API request handling
- `[WS]` - WebSocket events
- `[BROWSER]` - Browser console (filtered)