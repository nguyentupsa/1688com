# Gate Control API

## Manual Control of Negotiation Flow

The negotiation agent now supports manual gate control at 3 checkpoints:

### API Endpoints

**Open Gate (continue to next step):**
```
POST /api/gate/open?name=CONFIRM_AFTER_LOGIN
POST /api/gate/open?name=CONFIRM_PRODUCT_AND_CHAT
POST /api/gate/open?name=CONFIRM_AFTER_SEND
```

**Reset Gate (if needed):**
```
POST /api/gate/reset?name=<gate_name>
```

### Flow with Gates

1. **S0_DONE** → Wait for `CONFIRM_AFTER_LOGIN` (180s timeout)
   - After successful login and modal disappears

2. **S1_DONE** → Wait for `CONFIRM_PRODUCT_AND_CHAT` (120s timeout)
   - After product opened and chat window ready

3. **S2_DONE** → Wait for `CONFIRM_AFTER_SEND` (60s timeout)
   - After opener message sent

### Usage Examples

**Fully Automatic:** Let gates timeout automatically

**Semi-Manual:** Open specific gates when ready
```bash
# After confirming login is complete
curl -X POST "http://localhost:8000/api/gate/open?name=CONFIRM_AFTER_LOGIN"

# After confirming chat is open and ready
curl -X POST "http://localhost:8000/api/gate/open?name=CONFIRM_PRODUCT_AND_CHAT"

# After confirming opener was sent
curl -X POST "http://localhost:8000/api/gate/open?name=CONFIRM_AFTER_SEND"
```

**Frontend Integration:** Monitor WebSocket logs for S0_DONE/S1_DONE/S2_DONE states, then display appropriate confirmation buttons that call the gate APIs.