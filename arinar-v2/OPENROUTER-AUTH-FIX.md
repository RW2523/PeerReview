# OpenRouter API Authentication Fix - Feb 11, 2026

## Problem
When launching meeting and auto-triggering first agent turn, getting error:
```
POST /debates/{id}/turn/next 500 (Internal Server Error)
Failed to trigger next turn: Internal Server Error
```

## Root Cause
OpenRouter API authentication failure:
```
OpenRouter API error (status 502): {
  "error": {
    "message": "Failed to authenticate request with Clerk",
    "code": 502
  }
}
```

This means the OpenRouter API key is either:
1. **Invalid or expired**
2. **Not properly formatted** (should start with `sk-or-v1-...`)
3. **Lacks required permissions** (needs chat completion access)
4. **Temporary OpenRouter service issue** (Clerk auth system down)

---

## Solution

### Step 1: Verify Your OpenRouter API Key

1. Go to [OpenRouter Dashboard](https://openrouter.ai/keys)
2. Check your API key:
   - Format: `sk-or-v1-...` (new format) or `sk-...` (legacy)
   - Status: Active (not expired or disabled)
   - Credits: Has available balance
   - Permissions: Has "Chat Completion" access

### Step 2: Get a Fresh API Key

If key is invalid or expired:
1. Visit https://openrouter.ai/keys
2. Click "Create New Key"
3. Copy the new key (starts with `sk-or-v1-...`)
4. **Save it securely** (can't view again!)

### Step 3: Update Key in Arinar

**Option A: Via Settings Page**
1. In Arinar, click your profile/settings icon
2. Navigate to "OpenRouter API Key" section
3. Paste your new key
4. Click "Save"

**Option B: Via Browser localStorage** (temporary testing)
```javascript
// In browser console (F12)
localStorage.setItem('openrouter_api_key', 'sk-or-v1-YOUR-KEY-HERE');
location.reload();
```

### Step 4: Test the Key

Before launching meeting, test your key:
1. Go to Settings page
2. Click "Test API Key" or check account info
3. Should show: ✅ "Connected" with credit balance
4. If fails: ❌ "Invalid API key" - get a new one

---

## What I Fixed

### Better Error Messages

**Before:**
```
500 Internal Server Error
Failed to trigger next turn: Internal Server Error
```

**After:**
```
500 Internal Server Error
Failed to trigger next turn: OpenRouter API authentication failed. 
Please check your API key or try again later.
```

**File Modified:** `apps/api/src/routes/turns.py`

Added specific error detection:
- 502 errors → "authentication failed, check key"
- 401 errors → "invalid API key, update in Settings"
- Network errors → "OpenRouter service unavailable"

---

## Testing After Fix

1. **Update API key** (see Step 3)
2. **Create new meeting** in setup flow
3. **Run preflight** (should complete)
4. **Launch meeting**
5. **Wait 3-5 seconds**
6. **Check result:**
   - ✅ Success: First agent message appears
   - ❌ Fail: See clear error message with action

---

## Common OpenRouter Issues

### Issue 1: "502 Clerk authentication"
**Cause:** Key invalid, expired, or OpenRouter service issue  
**Fix:** Get fresh API key from openrouter.ai

### Issue 2: "401 Unauthorized"
**Cause:** Key format wrong or doesn't exist  
**Fix:** Check key starts with `sk-or-v1-` or `sk-`

### Issue 3: "Insufficient credits"
**Cause:** OpenRouter account has $0 balance  
**Fix:** Add credits at https://openrouter.ai/credits

### Issue 4: "Model not found"
**Cause:** Agent configured with unavailable model  
**Fix:** Use common models like:
- `openai/gpt-4o-mini`
- `openai/gpt-4o`
- `anthropic/claude-3.5-sonnet`

---

## Temporary Workaround

If OpenRouter is down or you can't fix the key:

1. **Manual Turn Trigger** - Skip auto-trigger, use "Next Turn" button manually
2. **Different Model** - Try another agent template with different model
3. **Wait & Retry** - OpenRouter Clerk auth issues are usually temporary (5-30 min)

---

## Next Steps

1. ✅ Get valid OpenRouter API key
2. ✅ Update key in Arinar Settings
3. ✅ Test key (check account endpoint)
4. ✅ Launch meeting again
5. ✅ First agent should speak automatically!

---

## Support

If issue persists after getting fresh key:
- Check OpenRouter status: https://status.openrouter.ai/
- Check OpenRouter Discord: https://discord.gg/openrouter
- Verify credits balance: https://openrouter.ai/activity
