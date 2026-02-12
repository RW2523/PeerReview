# SSE Stream Debugging Findings

## Summary
I've investigated the SSE stream and found that **the backend is sending clean, properly formatted data**. The "System UNKNOWN" spam is NOT coming from the backend.

## Backend Investigation Results

### 1. Database Check ✅ CLEAN
```
Total events: 6
- system_message: 3 (filtered out by frontend)
- agent_message: 2 (should be displayed)
- presence_update: 1 (filtered out by frontend)
```

No NULL event_types, no spam, no duplicate events.

### 2. SSE Stream Check ✅ CLEAN
I connected directly to the SSE endpoint and captured the raw stream:

```
event: debate_event
data: {"event_id": "dc55941f-7863-4f53-bbb8-594bf1bbc8e3", "debate_id": "ff97d8d1-c9e3-4c0e-b347-9a9bdb88c489", "event_type": "agent_message", "sequence_number": 2, "occurred_at": "2026-02-12T02:05:11.599546+00:00", "payload": {"text": "", "turn": 1, "model": "moonshotai/kimi-k2.5", "agent_name": "Car Enthusiast", "turn_index": 0}}

event: debate_event
data: {"event_id": "99c0f6ba-15d0-42a3-93c7-1296dbe65fff", "debate_id": "ff97d8d1-c9e3-4c0e-b347-9a9bdb88c489", "event_type": "agent_message", "sequence_number": 4, "occurred_at": "2026-02-12T02:05:24.365645+00:00", "payload": {"text": "...", "turn": 2, "model": "openai/gpt-oss-safeguard-20b", "agent_name": "Automotive Engineer", "turn_index": 1}}

event: state_update
data: {"debate_id": "ff97d8d1-c9e3-4c0e-b347-9a9bdb88c489", "state": "ended", "updated_at": "2026-02-12T02:09:18.750458+00:00"}

event: stream_end
data: {"reason": "debate_ended"}
```

**All events have proper:**
- ✅ `event_type` fields
- ✅ `agent_name` in payload
- ✅ Proper structure
- ✅ No spam or duplicates

### 3. Backend Filtering ✅ CORRECT
The `stream_service.py` correctly filters out noisy events:
```python
# Lines 49-52, 90-94
if not evt_type or evt_type in ['system_message', 'presence_update', 'typing', 'heartbeat', 'keepalive']:
    continue
```

## Frontend Investigation

### EventFeed.tsx Filtering ✅ CORRECT
```typescript
// Lines 71-96
const shouldFilterOut = [
  'keepalive',
  'heartbeat',
  'presence_update',
  'typing',
  'system_message',  // Hide all system state changes
];

if (shouldFilterOut.includes(event.event_type)) {
  return; // Don't add to feed
}
```

### EventCard Display Logic
```typescript
// Lines 225-228
const getActor = () => {
  if (event.payload?.agent_name) return event.payload.agent_name;
  if (event.payload?.actor) return event.payload.actor;
  return 'System';  // <-- Shows "System" when no agent info
};

// Line 243
<span className={styles.eventType}>{event.event_type || 'unknown'}</span>
```

"System UNKNOWN" would only appear if:
- `event.payload.agent_name` is missing/undefined
- `event.payload.actor` is missing/undefined
- `event.event_type` is missing/undefined

But the SSE stream shows both fields are present!

## Possible Causes of Frontend Spam

Since the backend is clean, the spam must be caused by:

1. **Multiple SSE connections** - EventFeed might be connecting multiple times
2. **React re-renders** - Component remounting and reconnecting
3. **Stale/cached events** - Old events from a previous session
4. **Different debate_id** - Frontend might be using a different debate ID
5. **Browser DevTools issue** - Multiple tabs or windows open
6. **SSE reconnection loop** - Client reconnecting too frequently

## Debugging Tools Created

### 1. `test_sse.py`
Direct Python script to connect to SSE and see raw stream data.
```bash
cd arinar-v2
python3 test_sse.py
```

### 2. `test_frontend_sse.html`
HTML page that simulates the frontend SSE client.
```bash
cd arinar-v2
open test_frontend_sse.html
# Or: python3 -m http.server 8080
# Then visit: http://localhost:8080/test_frontend_sse.html
```

## Recommended Next Steps

### To See the Actual SSE Data in Browser:

1. **Open DevTools** (F12 or Cmd+Option+I)

2. **Go to Network Tab**
   - Filter by "EventStream" or "stream"
   - Look for: `debates/{debate_id}/events/stream`
   - Click on it

3. **View EventStream Messages**
   - In Chrome: Click "EventStream" sub-tab
   - In Firefox: Click "Response" tab
   - You should see the SSE messages in real-time

4. **Check Console Tab**
   - Look for errors
   - Look for console.log statements from EventFeed
   - Check for warnings about duplicate keys

5. **Check for Multiple Connections**
   - In Network tab, see if there are multiple SSE connections
   - Each connection should show as a separate row

### To Debug the Frontend:

Add this to `EventFeed.tsx` after line 62:

```typescript
const event = JSON.parse(msg.data);

// DEBUG: Log every received event
console.log('[EventFeed DEBUG]', {
  sseEvent: msg.event,
  eventType: event.event_type,
  actor: event.payload?.agent_name || event.payload?.actor || 'NONE',
  hasEventType: !!event.event_type,
  hasAgentName: !!event.payload?.agent_name,
  fullEvent: event
});
```

Then reload the page and check the console.

### To Check for Multiple Mounts:

Add this to `EventFeed.tsx` at line 31 (inside the component):

```typescript
useEffect(() => {
  console.log('[EventFeed] MOUNTED for debate:', debateId);
  return () => {
    console.log('[EventFeed] UNMOUNTED for debate:', debateId);
  };
}, [debateId]);
```

If you see multiple MOUNTED messages without UNMOUNTED, that's the problem.

## Conclusion

**The backend SSE stream is working correctly and sending clean data.**

The "System UNKNOWN" spam is a frontend issue, likely caused by:
- Multiple component mounts
- SSE reconnection issues
- Event duplication in state management

The debugging tools and steps above will help identify the exact cause.
