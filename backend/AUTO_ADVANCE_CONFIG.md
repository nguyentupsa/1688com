# Auto-Advance Gates Configuration

This feature allows the bot to automatically run the full negotiation sequence without manual intervention.

## Environment Variables

Add these environment variables to enable auto-advance:

```bash
# Enable automatic gate advancement
AUTO_ADVANCE_GATES=1

# Timeout for each gate (in seconds)
AUTO_ADVANCE_TIMEOUT=1.0
```

## Running with Auto-Advance

### Direct Python/uvicorn
```bash
AUTO_ADVANCE_GATES=1 AUTO_ADVANCE_TIMEOUT=1.0 uvicorn app:app --host 0.0.0.0 --port 8000
```

### Docker Compose (if using)
```yaml
environment:
  - AUTO_ADVANCE_GATES=1
  - AUTO_ADVANCE_TIMEOUT=1.0
```

## How It Works

The auto-advance feature automatically passes through these gates:
- `CONFIRM_AFTER_LOGIN` - After login completion
- `CONFIRM_PRODUCT_AND_CHAT` - After navigating to product and opening chat
- `CONFIRM_AFTER_SEND` - After sending opener message

When enabled, each gate will automatically advance after the configured timeout (default 1.0 second).

## API Usage

### Start Full Negotiation
```powershell
Invoke-RestMethod -Method POST http://localhost:8000/api/negotiate/start `
  -Body (@{
    product_url = "https://detail.1688.com/offer/925677632684.html"
    opener_text = "你好，我对这款产品感兴趣。请问MOQ、单价、运费和交期是多少？支持定制和开票吗？谢谢！"
    style = "Aggressive"
  } | ConvertTo-Json) `
  -ContentType "application/json"
```

### Check Status
```powershell
Invoke-RestMethod http://localhost:8000/api/negotiation/status | ConvertTo-Json -Depth 5
```

## Flow

With auto-advance enabled, the bot will:
1. **S0**: Login and wait 1s → auto-advance
2. **S1**: Navigate to product + open chat and wait 1s → auto-advance
3. **S2**: Send opener and wait 1s → auto-advance
4. **S3**: Wait for supplier reply and respond with AI

The full sequence runs automatically without any manual intervention needed!