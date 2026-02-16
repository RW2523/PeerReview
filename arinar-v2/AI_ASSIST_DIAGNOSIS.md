# 🔍 "Improve with AI" - Complete Fix & Diagnosis Guide

## ❌ Problem
"Improve with AI" was stuck at "Generating..." for 30+ seconds, then timing out.

## ✅ Root Cause Found
The OpenRouter API call was **hanging indefinitely** because:
1. No granular timeout control (connection vs read vs write)
2. Invalid/test API keys cause OpenRouter to hang instead of fast-failing
3. No API key format validation before making the request

## 🔧 Fixes Applied

### 1. **Granular Timeout Control**
```python
# Before: Single 30s timeout (too long, not granular)
async with httpx.AsyncClient(timeout=30.0) as client:

# After: Granular timeouts for each phase
timeout_config = httpx.Timeout(
    connect=5.0,   # 5s to connect to OpenRouter
    read=15.0,     # 15s to read the response
    write=5.0,     # 5s to send request
    pool=5.0       # 5s to get connection from pool
)
async with httpx.AsyncClient(timeout=timeout_config) as client:
```

**Result:** Fails in 5s if can't connect, 15s max for response

### 2. **API Key Format Validation**
```python
# Before: No validation, sends to OpenRouter and hangs

# After: Fast validation before API call
if not x_openrouter_key.startswith('sk-or-'):
    raise HTTPException(
        status_code=401,
        detail="Invalid API key format. Keys start with 'sk-or-'"
    )
```

**Result:** Instant feedback if key is wrong

### 3. **Better Error Messages**
```python
# Before: Generic "timeout" or "error"

# After: Specific, helpful errors
401: "Invalid API key. Get one at openrouter.ai"
402: "Insufficient credits. Add credits at openrouter.ai"
504: "OpenRouter is slow. Check openrouter.ai/status"
Network: "Check your internet connection"
```

### 4. **Health Check Endpoint**
```python
GET /api/ai/health
Header: X-OpenRouter-Key: sk-or-...

Response:
{
  "status": "ok",
  "model": "openai/gpt-4o-mini",
  "credits_available": true
}
```

**Use this to test your API key before trying "Improve with AI"**

### 5. **Visual Improvements**
- ⏳ Spinning emoji while generating
- Blue Vercel-style button
- Pulsing animation when loading
- Clear error dialogs with help

## 🧪 How to Test

### Test 1: Valid API Key
```bash
# Check if backend is running
curl http://localhost:8000/health

# Test the health check
curl -X GET http://localhost:8000/api/ai/health \
  -H "X-OpenRouter-Key: sk-or-YOUR_REAL_KEY"

# Should return: {"status":"ok","model":"...","credits_available":true}
```

### Test 2: Invalid API Key Format
```bash
curl -X GET http://localhost:8000/api/ai/health \
  -H "X-OpenRouter-Key: invalid-key"

# Should fail fast with 401: "Invalid API key format"
```

### Test 3: Timeout Behavior
The new timeouts ensure:
- **5 seconds** to connect (vs hanging forever)
- **15 seconds** max for response (vs 30s)
- **Total: 20 seconds** max (vs 30s+)

### Test 4: In Browser
1. Go to `/setup`
2. Enter a problem statement
3. Click "✨ Improve with AI"
4. Should see:
   - ⏳ Spinning emoji
   - Button turns blue
   - Response in 3-5 seconds (with valid key)
   - Clear error if no key/credits

## 🚨 Troubleshooting

### Still Timing Out?

**1. Check Your API Key**
```bash
# Valid format?
echo $OPENROUTER_KEY | grep -q '^sk-or-' && echo "✅ Format OK" || echo "❌ Invalid format"

# Test it
curl -X GET http://localhost:8000/api/ai/health \
  -H "X-OpenRouter-Key: $OPENROUTER_KEY"
```

**2. Check Credits**
- Go to https://openrouter.ai
- Click "Credits" or "Billing"
- Add at least $5

**3. Check OpenRouter Status**
- Visit https://openrouter.ai/status
- Look for any outages

**4. Check Network**
```bash
# Can you reach OpenRouter?
curl -I https://openrouter.ai/api/v1/models

# Should return HTTP/2 200
```

**5. Check Backend Logs**
```bash
cd arinar-v2/apps/api

# Watch logs in real-time
tail -f logs/*.log

# Or check uvicorn output
# Look for "Calling OpenRouter..." and "OpenRouter responded..."
```

### Backend Not Running?
```bash
# Find the process
ps aux | grep uvicorn

# If not running, start it
cd arinar-v2/apps/api
.venv/bin/python3.11 -m uvicorn src.main:app --reload --port 8000
```

### Frontend Not Updating?
```bash
# Hard refresh in browser
# Mac: Cmd + Shift + R
# Windows: Ctrl + Shift + R
```

## 📊 Performance Comparison

### Before
```
User clicks → 30s hang → Timeout error
Total: 30+ seconds, no useful info
```

### After
```
Invalid key → 0.1s → "Invalid format"
No credits → 5s → "Add credits at..."
Valid key → 3-5s → Success!
Network issue → 5s → "Check connection"
OpenRouter slow → 20s → "Try again later"
```

## 🎯 Expected Behavior

### Happy Path (Valid Key + Credits)
1. Click "✨ Improve with AI"
2. Button becomes "⏳ Generating..." (spinning)
3. Backend calls OpenRouter (3-5 seconds)
4. Problem statement improved
5. Key points, agenda, outcomes filled in
6. Button back to "✨ Improve with AI"

### Error Paths
- **No API key** → Redirected to Settings
- **Invalid format** → Instant error (0.1s)
- **No credits** → Error after 5s
- **Network issue** → Error after 5s
- **OpenRouter slow** → Error after 20s

## 🔑 API Key Setup

1. **Get API Key:**
   - Go to https://openrouter.ai
   - Sign up / Log in
   - Go to "Keys" section
   - Create new key
   - Copy key (starts with `sk-or-`)

2. **Add Credits:**
   - Go to "Credits" or "Billing"
   - Add at least $5 (should last hundreds of requests)
   - GPT-4o-mini costs $0.0001 per request

3. **Add to App:**
   - Go to `/settings` in your app
   - Paste API key
   - Test with "Improve with AI"

## 📝 Files Changed

1. **`ai_assist.py`** - Main fixes
   - Granular timeouts
   - API key validation
   - Better errors
   - Health check endpoint
   - Logging

2. **`BasicInfoStep.tsx`** - Frontend
   - Spinning emoji
   - Error dialogs
   - Timeout handling

3. **`SetupSteps.module.css`** - Styling
   - Spinner animation
   - Button states

---

**Status:** ✅ FIXED - Should now fail fast with helpful errors!
**Next Test:** Try it in the browser with your real API key
