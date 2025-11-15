# Login Helper Patches - Apply Instructions

## Apply Patches

```bash
cd backend
patch -p1 < login_helpers.patch
patch -p1 < state_machine_check.patch
```

## What's Fixed

### 1. playwright_driver.py
**Added 2 new helpers:**
- `_is_logged_in(page)` - Check login status via UI heuristics
- `_wait_offer_ready(page)` - Wait for product page to be ready
- `_mute_console(page)` - Filter APLUS and sensor noise

**Enhanced ensure_login_via_taobao():**
- Added post-login navigation logic
- Work Home ping to "fix guards"
- Product page navigation with retry (2 attempts)
- Login modal visibility check to confirm success

### 2. state_machine.py
**Added product page readiness check:**
- Calls `_wait_offer_ready()` after login
- Auto-reload if page not ready
- Clear error messages if navigation fails
- Enhanced logging throughout the flow

## Key Features

✅ **Smart Login Detection**
- UI heuristics: greeting messages, avatar, work links
- Stable login confirmation

✅ **Product Page Verification**
- Waits for detail content to be visible
- Auto-reload on failure
- Clear error reporting

✅ **Console Noise Filtering**
- Blocks APLUS analytics messages
- Filters permission violations
- Clean log output

✅ **Post-Login Navigation**
- Work Home ping for session stability
- Direct product navigation
- Retry logic with modal visibility check

## Flow After Patches

1. **Login Process**
   - Detect login need automatically
   - Wait for modal to disappear
   - Confirm login via UI heuristics

2. **Post-Login Navigation**
   - Ping Work Home (fixes session)
   - Navigate to product URL
   - Verify product page readiness
   - Auto-reload if needed

3. **Error Recovery**
   - Clear error messages
   - Manual intervention prompts
   - Graceful degradation

## Expected Results

✅ No more "standing still" after login
✅ Clean console output (no APLUS spam)
✅ Reliable product page navigation
✅ Clear error messages when manual help needed

Apply the patches now and the login flow should work smoothly! 🚀