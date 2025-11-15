# Noise & Error Fix Application

## Current Issues Identified

From the logs, I see:
1. **Massive console noise** - APLUS, permissions violations, endGroup errors
2. **Login detection working** - "当前登录弹窗为 1.0.0 版本" detected
3. **Negotiation start error** - System fails during startup with generic error

## Apply Patches

```bash
cd backend
patch -p1 < noise_filter.patch
patch -p1 < error_handling.patch
patch -p1 < state_error_fix.patch
```

## What These Patches Fix

### 1. noise_filter.patch
**Expanded noise filtering to cover all current noise:**
- APLUS messages and script timing warnings
- All permission policy violations (gyroscope, accelerometer, etc.)
- Console endGroup errors
- Login popup detection messages (keep important ones)
- Resource blocking errors

### 2. error_handling.patch
**Better error handling in API:**
- More detailed logging for negotiation start
- Clear error messages with exception types
- Debug logging with full traceback when errors occur

### 3. state_error_fix.patch
**Enhanced state machine error tracking:**
- Detailed logging at each major step
- Clear error messages when login/chat fails
- Full traceback logging for debugging
- Better session state management

## Expected Results

After applying these patches:
✅ **Clean console output** - Only relevant logs will show
✅ **Better error visibility** - Clear error messages instead of generic failures
✅ **Debugging capability** - Full tracebacks when things go wrong
✅ **Stable login detection** - Login modal detection should work properly

## Apply Now

```bash
cd backend
patch -p1 < noise_filter.patch
patch -p1 < error_handling.patch
patch -p1 < state_error_fix.patch
```

Then restart the backend and test again. The logs should be much cleaner and errors more informative!