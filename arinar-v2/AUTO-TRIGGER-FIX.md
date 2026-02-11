# Auto-Trigger First Agent Fix - Feb 11, 2026

## Problem
When user launches meeting from setup flow, room page loads but **no agents speak**. The user sees an empty Live Feed and has to manually discover the "Next Turn" button.

## Root Cause
The `handleLaunchDebate` function only:
1. Starts the debate (changes state to "running")
2. Navigates to room page

It does NOT trigger the first agent to speak.

## Solution
Modified `handleLaunchDebate` to **auto-trigger first agent turn** immediately after starting the debate:

### Flow Now:
1. User clicks "Launch Meeting" (Step 6)
2. Backend: `startDebate()` - changes state to "running"
3. **NEW**: Frontend: `triggerNextTurn()` - first agent starts speaking
4. Navigate to room page
5. User sees first agent message in Live Feed (or agent is currently thinking)

### Implementation
**File**: `apps/web/src/hooks/useDebateSetupActions.ts`

Added between start and navigation:
```typescript
// 2. Auto-trigger first agent turn
console.log('🤖 Auto-triggering first agent turn...');
try {
  await api.triggerNextTurn(debateId, apiKey);
  console.log('✅ First agent turn triggered successfully');
} catch (turnErr: any) {
  console.error('⚠️ Failed to auto-trigger first turn:', turnErr);
  // Don't block navigation, user can manually trigger in room
}
```

### Error Handling
- If first turn fails to trigger (e.g., API key invalid, network issue), **navigation still proceeds**
- Error is logged to console
- User can manually click "Next Turn" button in room as fallback

## User Experience

### Before:
1. Launch meeting
2. Room loads - **EMPTY**
3. User confused: "Nothing is happening?"
4. User has to discover and click "Next Turn" button

### After:
1. Launch meeting
2. **First agent starts thinking immediately**
3. Room loads - sees "Agent thinking..." or first message
4. Conversation has begun!

## Testing
- [x] Verify `triggerNextTurn` is called after `startDebate`
- [x] Verify navigation happens after trigger (not blocked)
- [x] Verify error handling (bad API key doesn't crash)
- [ ] End-to-end test: Setup → Launch → See first agent message

## Notes
- API key is required and validated before launch
- First turn uses OpenRouter API (BYOK model)
- Turn orchestrator respects participant order (based on creation order currently)
- Future: Use turn order defined in Step 3 (requires backend update)
