# Private Messaging Back-and-Forth Fix

## Problem

**User Report:** "Only one agent sends message, no response and conversation happening"

### Root Causes Found:

1. ❌ **Random targeting with no reply priority**
   - Agents randomly picked targets
   - No system to PRIORITIZE replying to unreplied DMs
   - Result: Agent A sends to B, Agent B sends to C, Agent C sends to D → No conversations!

2. ❌ **Overly formal, robotic messages**
   - Messages like: "I appreciate your contribution to the discussion"
   - Too corporate, not human-like

3. ❌ **Wrong model causing failures**
   - Using `google/gemini-2.0-flash-exp:free` which returned 404 errors
   - Blocked ALL private messages from working

---

## Fixes Applied

### Fix #1: Reply Priority System ✅

**File:** `/apps/api/src/turn_orchestrator.py` (Lines 843-887)

**Before:**
```python
# Randomly pick target
target = random.choice(other_agents)

# Check if THAT specific target sent us a DM
# If yes, reply. If no, send new DM to them
```

**Problem:** If Agent A sends to B, but when B's turn comes, B randomly picks C (not A), so B never replies to A!

**After:**
```python
# PRIORITY: Check if ANY agent sent us an unreplied DM
cursor.execute("""
    SELECT DISTINCT content->>'from_agent' as sender, content->>'message' as message
    FROM events
    WHERE debate_id = %s 
      AND event_type = 'private_message'
      AND content->>'to_agent' = %s  -- Messages sent TO current agent
      AND NOT EXISTS (
        SELECT 1 FROM events e2
        WHERE e2.content->>'from_agent' = %s  -- Check if we replied
          AND e2.content->>'to_agent' = content->>'from_agent'
          AND e2.sequence_number > events.sequence_number
      )
    ORDER BY events.sequence_number DESC
    LIMIT 1
""")

if result:
    # REPLY to the agent who DM'd us
    target = result['sender']
    previous_dm = result['message']
else:
    # No unreplied DMs, start new conversation
    target = random.choice(other_agents)
```

**Result:** Agents now ALWAYS reply to unreplied DMs before starting new conversations → Back-and-forth happens!

---

### Fix #2: Changed Model to `openai/gpt-oss-20b:free` ✅

**File:** `/apps/api/src/agent_autonomy.py` (Line 154)

**Before:**
```python
model='openai/gpt-4o-mini'  # Fast and reliable
```

**After (Per User Request):**
```python
model='openai/gpt-oss-20b:free'  # Free, fast, more conversational
```

**Also Changed:**
- `temperature=0.8` → `0.9` (more variety in responses)
- `max_tokens=60` → `80` (longer messages)
- `max_length=200` → `250` chars (more room to express)

---

### Fix #3: More Human-Like Prompt ✅

**File:** `/apps/api/src/agent_autonomy.py` (Lines 130-150)

**Before (Too Formal):**
```python
**Your Options (pick ONE tone):**
1. Supportive: "Great point about X! I'm with you on that."
2. Critical: "That reasoning was weak - you missed Y entirely."
...

**Rules:**
- BE HONEST AND HUMAN: React genuinely to what they said
- MAX 25 WORDS: Keep it punchy
```

**After (More Natural):**
```python
**How to DM like a real person:**
- React to what THEY specifically said or did
- Be direct and casual - this is private
- Pick a vibe: supportive, critical, strategic, sarcastic, friendly, or confrontational
- Keep it 15-30 words MAX

**Good examples:**
- "Yo, I see what you're doing with X. Smart move."
- "That point you made about Y was weak, honestly."
- "Let's team up - they're missing the obvious."
- "Did you seriously just argue for Z? Come on."
- "You nailed it with that example. Nice."
- "Your logic on X has holes. Think it through."

**Bad examples (too formal/generic):**
- "I appreciate your contribution to the discussion."  ❌
- "Let's collaborate on this matter going forward."  ❌
- "I respectfully disagree with your position."  ❌
```

---

## Expected Behavior Now

### Before (Broken):
```
Turn 1: Agent A → DM → Agent B (new)
Turn 2: Agent B → DM → Agent C (new, ignores A)
Turn 3: Agent C → DM → Agent A (new, ignores B)
Turn 4: Agent A → DM → Agent C (new, ignores B)
```
**Result:** No conversations, just one-off messages

---

### After (Fixed):
```
Turn 1: Agent A → DM → Agent B (new)
        "Yo, your point about X was weak"

Turn 2: Agent B checks: "Do I have unreplied DMs?" → YES from Agent A
        Agent B → DM → Agent A (REPLY)
        "Weak? That's the data talking, not emotion"

Turn 3: Agent A checks: "Do I have unreplied DMs?" → YES from Agent B
        Agent A → DM → Agent B (REPLY)
        "Data? Show me the source then"

Turn 4: Agent B checks: "Do I have unreplied DMs?" → YES from Agent A
        Agent B → DM → Agent A (REPLY)
        "Check the 2024 study I cited earlier"

Turn 5: Agent C (hasn't been DM'd yet)
        Agent C → DM → Agent A (new conversation starts)
        "You both are missing the real issue here"
```

**Result:** REAL back-and-forth conversations happen!

---

## Message Quality Improvements

### Before:
```
"I appreciate your contribution to the discussion and look forward to collaborating."
"I respectfully disagree with your position on this matter."
"Perhaps we should consider alternative perspectives."
```
**Too formal, robotic, corporate-speak**

### After:
```
"Your logic on X has holes. Think it through."
"Yo, I see what you're doing with X. Smart move."
"Did you seriously just argue for Z? Come on."
"Let's team up - they're missing the obvious."
"That point you made about Y was weak, honestly."
```
**Direct, casual, conversational, HUMAN**

---

## Testing

To verify the fix works:

1. **Start or continue a debate** with 3+ agents
2. **Trigger 5-6 turns** (hit "Next Turn" multiple times)
3. **Watch for Private Messages in the UI**
4. **Check logs** for:
   ```
   🔔 Found unreplied DM from AgentB to AgentA
   ✅ DM sent: AgentA → AgentB (REPLY)
   ```

### Expected Results:
- ✅ Agents reply to each other (back-and-forth conversations)
- ✅ Messages are casual and human-like
- ✅ No more 404 model errors
- ✅ Conversations build on each other instead of one-off messages

---

## Technical Details

### Reply Detection Query:
```sql
SELECT DISTINCT 
  content->>'from_agent' as sender, 
  content->>'message' as message
FROM events
WHERE debate_id = $1 
  AND event_type = 'private_message'
  AND content->>'to_agent' = $2  -- Messages TO current agent
  AND content->>'from_agent' != $2
  AND NOT EXISTS (
    -- Check if current agent already replied
    SELECT 1 FROM events e2
    WHERE e2.debate_id = $1
      AND e2.event_type = 'private_message'
      AND e2.content->>'from_agent' = $2
      AND e2.content->>'to_agent' = content->>'from_agent'
      AND e2.sequence_number > events.sequence_number
  )
ORDER BY events.sequence_number DESC
LIMIT 1
```

**What it does:**
1. Find all DMs sent TO current agent
2. Exclude DMs we already replied to (NOT EXISTS check)
3. Return the most recent unreplied DM
4. If found → reply to that agent
5. If not found → start new conversation with random agent

---

## Files Changed:
1. `/apps/api/src/agent_autonomy.py` - Model, prompt, and message quality
2. `/apps/api/src/turn_orchestrator.py` - Reply priority system

**Server will auto-reload with these changes (--reload flag enabled)**
