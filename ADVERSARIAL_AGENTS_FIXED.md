# 🔥 Agents Now Set to DEBATE MODE! 

## ❌ The Problem - "Sweet Talking"

Your agents were being too polite and agreeable because the prompts said:
- ❌ "BUILD ON others" → Agents just agreed
- ❌ "BE OPEN-MINDED" → No strong positions
- ❌ "REACT genuinely: Agree/disagree" → Mostly agreed
- ❌ "BE CONVERSATIONAL" → Too friendly

**Result**: Boring consensus, no debate!

---

## ✅ The Fix - ADVERSARIAL Mode

Changed the agent instructions to be **CONFRONTATIONAL**:

### New Instructions:

```
**Communication Style - BE ADVERSARIAL AND DEBATE:**
- CHALLENGE others: "I disagree with @TheirName because..."
- TAKE STRONG POSITIONS: Pick a side and defend it
- USE @mentions to ATTACK/DEFEND: "@Name, your assumption is wrong"
- DISAGREE with SPECIFIC points: "While @Name is right about A, they're wrong about B"
- ASK HARD QUESTIONS: "How do you justify X given Y?"
- BE COMPETITIVE: You're trying to WIN, not make friends
- QUESTION ASSUMPTIONS: Call out weak logic and flawed reasoning

FORBIDDEN PHRASES:
❌ "I agree with everything"
❌ "Great points all around"  
❌ "Both perspectives are valid"

GOOD PHRASES:
✅ "I strongly disagree"
✅ "That's incorrect because"
✅ "The evidence doesn't support that"
✅ "You're overlooking"
```

---

## 🎯 What You'll See Now

### Before (Sweet Talking):
```
Agent 1: "Great point about exercise being important!"
Agent 2: "I agree with everything Agent 1 said!"
Agent 3: "Both have valid perspectives, I see merit in all approaches..."
```

### After (Real Debate):
```
Agent 1: "I believe high-intensity training is essential"
Agent 2: "I disagree with @Agent1 - that's dangerous for asthma patients"
Agent 3: "@Agent2, where's your evidence? The research contradicts you"
```

---

## 🚀 How to Test NOW

### Step 1: Start Fresh Debate (Recommended)

The current debate has 3 polite turns. Best to start fresh:

1. Go to: http://localhost:3000/
2. Create new debate with same topic
3. Enable document feature
4. Start debate

### Step 2: OR Resume Current Debate

If you want to see the change in existing debate:

1. Go to: http://localhost:3000/room?debate_id=4b69cd26-3a32-4cad-b431-27863c1f6891
2. Click **"⏸️ RESUME"**
3. Watch the next turns - agents should start challenging each other!

---

## 📝 Document Feature Status

Added debug logging to trace document generation:

```
📝 _write_to_document_sections called:
   Agent: Medical Doctor (ID: ...)
   Debate: ...
   Message length: 342 chars
```

Check backend logs after next turn to see if:
1. Document generation is being called
2. Content is being generated
3. Content is being saved

If you don't see these logs, the document generation might not be triggering.

---

## 🔍 Debugging Steps

### 1. Check Backend Logs

After clicking RESUME, watch the terminal running the backend. Look for:
- `📝 _write_to_document_sections called:`
- `✅ Updated section: X words, status: Y`
- Any errors in document generation

### 2. Check Database Directly

```bash
curl -s "http://localhost:8000/debates/4b69cd26-3a32-4cad-b431-27863c1f6891/document" | python3 -m json.tool | grep -A 5 '"content"'
```

Should show actual text content, not `null` or empty strings.

### 3. Check Frontend

Go to Document tab and **hard refresh** (`Cmd+Shift+R`) after each turn.

---

## ✅ Summary

**Fixed:**
1. ✅ Agents now set to **ADVERSARIAL** mode
2. ✅ Will challenge, disagree, and debate
3. ✅ Added logging to trace document generation
4. ✅ Backend restarted with new behavior

**What to do:**
1. **Hard refresh** browser: `Cmd+Shift+R`
2. **Resume debate** or start a new one
3. **Watch agents fight!** 🔥
4. **Check backend logs** to see document generation

**Servers running:**
- Frontend: http://localhost:3000 ✅
- Backend: http://localhost:8000 ✅

**Try it now and tell me what you see! Are agents debating? Do you see content in Document tab?**
