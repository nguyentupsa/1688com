# Login Fix Application

## Apply Patches

```bash
cd backend
patch -p1 < login_fix.patch
patch -p1 < state_machine_fix.patch
```

## What Changed

### 1. playwright_driver.py

**New Helpers:**
- `_is_login_modal_visible()` - Detect login popup visibility
- `_is_logged_in()` - Check if user is logged in via UI heuristics
- `_wait_login_settled()` - Wait for login modal to disappear stably (800ms)
- `ensure_chat_ready()` - Wait for chat input to be available

**Simplified ensure_login_via_taobao():**
- Blocks popup tabs
- Auto-detects if login needed
- Waits for stable login (debounce 800ms)
- Routes through Work Home to fix session state
- Then navigates to product URL

### 2. state_machine.py

**Fixed Flow:**
- Calls ensure_login_via_taobao() with product URL
- Checks login result and raises error if failed
- Verifies product page is loaded with stable selectors
- Ensures chat input is ready before proceeding

## Key Improvements

✅ **No more hanging** - System detects login completion properly
✅ **Stable navigation** - Goes through Work Home to fix session
✅ **Debounce logic** - Waits 800ms after modal disappears
✅ **Error handling** - Clear error messages when login/chat fails
✅ **Auto-detection** - No manual login button clicking needed

## Apply Now

```bash
patch -p1 < login_fix.patch
patch -p1 < state_machine_fix.patch
```

The login flow should now work smoothly without hanging or getting stuck.