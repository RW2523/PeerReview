# How to Debug the SSE "System UNKNOWN" Spam Issue

## Quick Summary

I've investigated the SSE stream thoroughly and found that:

✅ **Backend is working correctly** - Only 6 clean events in database
✅ **SSE stream is clean** - Verified with direct connection test
✅ **No spam from backend** - All events have proper `event_type` and `agent_name`

❌ **The spam is happening in the frontend** - Likely due to multiple connections or React re-renders

## Step 1: Open the Page with DevTools

1. Navigate to: `http://localhost:3000/room?debate_id=ff97d8d1-c9e3-4c0e-b347-9a9bdb88c489`
2. Open DevTools: Press `F12` or `Cmd+Option+I` (Mac) or `Ctrl+Shift+I` (Windows/Linux)

## Step 2: Check the Console Tab FIRST

I've added comprehensive debugging logs. You should see:

```
[EventFeed] MOUNTING for debate: ff97d8d1-c9e3-4c0e-b347-9a9bdb88c489 at 2026-02-12T...
[SSEClient] Connecting to: http://localhost:8000/debates/.../events/stream at 2026-02-12T...
[SSEClient] Connected successfully to: http://localhost:8000/debates/.../events/stream
[EventFeed] SSE message received: {
  sseEventType: 'debate_event',
  eventType: 'agent_message',
  eventId: '...',
  sequenceNumber: 2,
  actor: 'Car Enthusiast',
  hasEventType: true,
  hasAgentName: true,
  willBeFiltered: false,
  timestamp: '...'
}
[EventFeed] Adding event to feed: ... agent_message
```

### What to Look For:

#### ❌ BAD: Multiple MOUNTING messages
```
[EventFeed] MOUNTING for debate: ... at 10:00:00
[EventFeed] MOUNTING for debate: ... at 10:00:01  <-- PROBLEM!
[EventFeed] MOUNTING for debate: ... at 10:00:02  <-- PROBLEM!
```
**This means:** EventFeed is being mounted multiple times, creating multiple SSE connections.

#### ❌ BAD: Messages with missing data
```
[EventFeed] SSE message received: {
  eventType: undefined,     <-- PROBLEM!
  actor: 'NONE',           <-- PROBLEM!
  hasEventType: false,     <-- PROBLEM!
  hasAgentName: false      <-- PROBLEM!
}
```
**This means:** The SSE message structure is wrong or being corrupted.

#### ❌ BAD: DUPLICATE messages
```
[EventFeed] DUPLICATE event ignored: abc-123
[EventFeed] DUPLICATE event ignored: abc-123
[EventFeed] DUPLICATE event ignored: abc-123  <-- Too many!
```
**This means:** Same event is being received multiple times.

#### ✅ GOOD: Clean sequence
```
[EventFeed] MOUNTING for debate: ... (only once)
[SSEClient] Connecting to: ... (only once)
[SSEClient] Connected successfully
[EventFeed] SSE message received: { eventType: 'agent_message', actor: 'Car Enthusiast', ... }
[EventFeed] Adding event to feed: ... agent_message
[EventFeed] SSE message received: { eventType: 'agent_message', actor: 'Automotive Engineer', ... }
[EventFeed] Adding event to feed: ... agent_message
[EventFeed] SSE message received: { eventType: 'state_update', willBeFiltered: false, ... }
[EventFeed] Adding event to feed: ... state_update
```

## Step 3: Check the Network Tab

1. Click on **Network** tab in DevTools
2. Look for a row with: `events/stream` or `stream`
3. You should see something like:
   ```
   Name: stream
   Status: 200
   Type: eventsource or text/event-stream
   ```

### What to Check:

#### ❌ BAD: Multiple stream connections
```
stream    200  eventsource  ...
stream    200  eventsource  ...  <-- DUPLICATE CONNECTION!
stream    200  eventsource  ...  <-- DUPLICATE CONNECTION!
```
**This means:** Multiple SSE connections are open simultaneously.

#### ✅ GOOD: Single stream connection
```
stream    200  eventsource  ...  (only one)
```

### View the EventStream Messages:

1. Click on the `stream` row in Network tab
2. In Chrome: Click the **EventStream** sub-tab
3. In Firefox: Click the **Response** tab
4. You should see the SSE messages:

```
event: debate_event
data: {"event_id":"...","event_type":"agent_message","payload":{"agent_name":"Car Enthusiast",...}}

event: debate_event
data: {"event_id":"...","event_type":"agent_message","payload":{"agent_name":"Automotive Engineer",...}}

event: state_update
data: {"debate_id":"...","state":"ended",...}

event: stream_end
data: {"reason":"debate_ended"}
```

**Take a screenshot of this!** This shows the actual data from the backend.

## Step 4: Check for Errors

In the Console tab, look for any red error messages:

```
❌ Failed to parse event: ...
❌ SSE error: ...
❌ Connection lost: ...
```

## Step 5: Count the Events

In the Console, type this command:

```javascript
// Count how many times EventFeed mounted
console.log('Mounting count:', performance.getEntriesByType('mark').filter(m => m.name.includes('MOUNTING')).length);

// Check current events in state (if you can access React DevTools)
// Or just count the visible events in the UI
```

Expected: **2 agent_message events should be visible** (after filtering)

If you see more than 2, that's the spam.

## Step 6: Alternative Testing

If the browser debugging is too complex, you can use the test files I created:

### Option A: Python Test Script
```bash
cd arinar-v2
python3 test_sse.py
```

This will show you the raw SSE stream data from the backend.

### Option B: HTML Test Page
```bash
cd arinar-v2
python3 -m http.server 8080
```

Then open: `http://localhost:8080/test_frontend_sse.html`

This simulates the frontend SSE client and shows exactly what data is received.

## Common Issues and Solutions

### Issue 1: React StrictMode Double-Mounting
**Symptom:** EventFeed mounts twice in development
**Solution:** This is normal in dev mode, but should only create one SSE connection
**Check:** Look for "Already connected" log message

### Issue 2: Fast Refresh Re-mounting
**Symptom:** EventFeed remounts on every code change
**Solution:** This is expected during development
**Check:** Verify UNMOUNTING happens before MOUNTING

### Issue 3: Multiple Browser Tabs
**Symptom:** Multiple SSE connections from different tabs
**Solution:** Close other tabs with the same page open
**Check:** Network tab shows multiple connections

### Issue 4: Reconnection Loop
**Symptom:** SSE keeps reconnecting rapidly
**Solution:** Check for errors causing disconnection
**Check:** Look for "Scheduling reconnect" messages

## What to Report Back

Please provide:

1. **Console logs** - Copy/paste the first 50 lines showing:
   - MOUNTING messages
   - SSE message received logs
   - Any errors

2. **Network tab screenshot** - Showing:
   - The EventStream connection(s)
   - The EventStream messages tab

3. **Event count** - How many events are visible in the UI?

4. **Spam description** - What exactly do you see?
   - "System UNKNOWN" appearing how many times?
   - Does it keep growing?
   - Does it happen immediately or after some time?

## Expected Behavior

With the current database state:
- ✅ 2 agent_message events should be visible in the feed
- ✅ "Car Enthusiast" and "Automotive Engineer" should be the actors
- ✅ No "System UNKNOWN" messages should appear
- ✅ No spam or duplicates

If you see anything different, the console logs will tell us exactly what's wrong!
