# ✅ REAL FIX APPLIED

## What I Just Found and Fixed

### The Real Problem:

Your screenshot shows "System UNKNOWN" - I traced this:

1. **"System"** = EventFeed.tsx line 228 - defaults to "System" when no agent_name
2. **"UNKNOWN"** = EventFeed.tsx line 243 - shows when `event.event_type` is null/undefined

### The Backend Filter Bug:

My previous filter checked:
```python
if event['event_type'] in ['system_message', ...]:
    continue
```

**BUG:** If `event_type` is NULL, it doesn't match any string, so NULL events pass through!

### The Fix (Just Applied):

```python
# NEW CODE:
evt_type = event.get('event_type')
if not evt_type or evt_type in ['system_message', ...]:
    continue  # Blocks NULL AND system_message events
```

**Lines changed:**
- `stream_service.py` line 48-51 (historical events)
- `stream_service.py` line 84-89 (polling new events)

### FastAPI Status:

✅ Server restarted with clean Python cache
✅ Filter updated
⏳ Waiting for auto-reload...

---

## 🧪 TEST IT NOW

### In Edge (already open):

1. Hard refresh: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
2. Go back to the debate room
3. Click "Next Turn"
4. Watch the Live Feed

### What You Should See:

- ✅ Agent messages with agent names
- ✅ Clean feed, no spam
- ❌ NO "System UNKNOWN" messages

### If Still Broken:

Then the issue is the SSE stream is reconnecting multiple times and resending old events. I'll need to:

1. Check why SSE keeps reconnecting
2. Fix the frontend to handle reconnection better
3. Or increase the `since_sequence` tracking

---

## My Next Move if This Doesn't Work:

I'll add aggressive logging to see:
1. What the SSE endpoint is actually sending
2. How many times the frontend is connecting
3. Whether duplicate event_ids are being sent

**Try it now and let me know!** 🙏
