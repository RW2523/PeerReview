# 🎯 GENERAL DEBATE FIX - Works for ANY Topic/Participants

## The Challenge
We can't hardcode positions like:
- ❌ "Medical Doctor MUST advocate indoor exercise" ← Too specific!
- ❌ "Tech CEO MUST push for AI regulation" ← Only works for one debate!

We need **STRUCTURAL RULES** that work for **ANY debate topic** with **ANY participants**.

---

## ✅ SOLUTION: 4-Layer Defense System

### Layer 1: DYNAMIC POSITION ASSIGNMENT (Topic-Agnostic)

Instead of hardcoding positions, **analyze the debate and extract dimensions**:

```python
def assign_diverse_positions(debate_topic, participants):
    """
    Extract key trade-off dimensions from ANY debate topic,
    then assign agents to different sides.
    """
    
    # Example for "Best workout for asthma patient":
    dimensions = {
        "safety_vs_results": ["prioritize_safety", "prioritize_results"],
        "indoor_vs_outdoor": ["indoor_focus", "outdoor_focus"],
        "cost": ["budget_conscious", "premium_solutions"],
        "time": ["quick_wins", "long_term_approach"]
    }
    
    # Example for "Should we regulate AI?":
    dimensions = {
        "regulation": ["heavy_regulation", "light_regulation"],
        "timeline": ["immediate_action", "gradual_approach"],
        "scope": ["global_standards", "national_control"],
        "enforcement": ["strict_penalties", "self_regulation"]
    }
    
    # ASSIGN EACH AGENT TO DIFFERENT SIDES
    for i, agent in enumerate(participants):
        agent.assigned_position = select_diverse_position(dimensions, i)
    
    return participants
```

**Result**: Agents automatically get different stances based on the topic!

---

### Layer 2: STRUCTURAL PROHIBITION (Works for Any Debate)

Ban behaviors that cause echo chambers, **regardless of topic**:

```python
UNIVERSAL_DEBATE_RULES = """
🚫 PROHIBITED BEHAVIORS (Rejected immediately):

1. AGREEMENT WITHOUT NEW INFO:
   ❌ "I agree with @Person..."
   ❌ "Great point by @Person..."
   ❌ "Building on what @Person said..."
   ✅ ONLY IF you add NEW evidence they didn't mention

2. REPEATED QUESTIONS:
   ❌ Asking a question already asked by another agent
   ❌ Asking the same question you asked before
   ✅ Ask NEW questions with new angles

3. VAGUE STATEMENTS:
   ❌ "We should consider..."
   ❌ "It's important to think about..."
   ❌ "We need to evaluate..."
   ✅ Specific recommendations with data/examples

4. ECHO CHAMBER:
   ❌ Repeating someone else's argument in different words
   ❌ Listing same factors as previous agent
   ✅ Introduce NEW factors not yet mentioned

✅ REQUIRED BEHAVIORS:

1. DISAGREE AT LEAST ONCE PER TURN:
   - Identify ONE point where you differ from others
   - Explain WHY with evidence
   - If you agree 100%, you're not thinking critically

2. ADD NEW INFORMATION:
   - Every message must introduce NEW facts/data/perspectives
   - Cannot just rephrase what others said
   - Must move discussion forward

3. BE SPECIFIC:
   - Include numbers, examples, protocols, or case studies
   - Avoid generic advice that applies to everything
   - Make your position FALSIFIABLE (can be proven wrong)
"""
```

**This works for ANY debate!** No topic-specific rules needed.

---

### Layer 3: ROUND-BASED PROGRESSION (Topic-Agnostic)

Force different behaviors per round:

```python
ROUND_STRUCTURE = {
    1: {
        "goal": "STAKE YOUR CLAIM",
        "rules": [
            "State your PRIMARY position clearly",
            "Provide initial evidence",
            "Questions allowed",
            "No need to disagree yet"
        ]
    },
    2: {
        "goal": "CHALLENGE OTHERS",
        "rules": [
            "Identify flaws in other positions",
            "Provide counter-evidence",
            "NO questions - only statements",
            "MUST disagree with at least 2 agents"
        ]
    },
    3: {
        "goal": "DEFEND & REFINE",
        "rules": [
            "Address criticisms of your position",
            "Acknowledge valid points from others",
            "Refine your stance if needed",
            "NO questions - only rebuttals"
        ]
    },
    4: {
        "goal": "SYNTHESIZE OR STAND FIRM",
        "rules": [
            "Final recommendation with full protocol",
            "Must be ACTIONABLE (not vague)",
            "Either compromise or explain why you won't",
            "NO questions - only conclusions"
        ]
    }
}
```

**Works for any debate length/topic!**

---

### Layer 4: SIMILARITY DETECTION (Fully Automated)

Detect repetition **regardless of topic**:

```python
def check_message_originality(new_message, debate_history):
    """
    Reject messages that are too similar to previous ones.
    Topic-agnostic using semantic similarity.
    """
    
    from sklearn.metrics.pairwise import cosine_similarity
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Get last 5 messages
    recent_messages = debate_history[-5:]
    
    # Compute similarity
    new_embedding = model.encode([new_message])
    recent_embeddings = model.encode(recent_messages)
    
    similarities = cosine_similarity(new_embedding, recent_embeddings)[0]
    max_similarity = max(similarities)
    
    if max_similarity > 0.70:  # 70% similar
        return {
            "approved": False,
            "reason": f"Message is {max_similarity:.0%} similar to previous message",
            "instruction": """
                Your message repeats previous points.
                You MUST either:
                1. Introduce a NEW perspective not yet discussed
                2. Provide NEW evidence/data not yet mentioned
                3. Challenge a specific claim with counter-evidence
            """
        }
    
    return {"approved": True}
```

**Automatic, no manual configuration needed!**

---

## 🔧 IMPLEMENTATION PLAN

### Step 1: Update System Prompt (topic-agnostic)

```python
UNIVERSAL_AGENT_PROMPT = """
You are {agent_name}, a {agent_role} participating in a structured debate.

Your assigned perspective: {dynamic_position}
(This ensures diverse viewpoints - you must advocate for this angle)

DEBATE RULES:

🎯 YOUR MISSION (Round {round_number}/4):
{round_specific_instructions}

🚫 PROHIBITED (Your message will be REJECTED if you):
- Agree without adding NEW information
- Ask questions already asked
- Use vague language ("consider", "think about")
- Repeat what others said in different words
- Exceed {word_limit} words

✅ REQUIRED (Every message MUST):
- Disagree with at least ONE other agent (with evidence)
- Add NEW information not yet mentioned
- Be SPECIFIC (numbers, examples, protocols)
- Move the discussion FORWARD

📊 CURRENT DEBATE STATUS:
- Topic: {debate_topic}
- Round: {round_number}/4
- Key questions raised: {key_questions}
- Positions so far: {position_summary}
- Gaps in discussion: {identified_gaps}

YOUR PREVIOUS STANCE: {your_previous_messages_summary}

Remember: You're here to CHALLENGE and ADVANCE the discussion, not to agree politely.
"""
```

---

### Step 2: Dynamic Position Assignment

```python
def extract_debate_dimensions(debate_topic, debate_description):
    """
    Use LLM to extract key trade-offs/dimensions from ANY debate topic.
    """
    
    prompt = f"""
    Analyze this debate topic and identify 3-5 key dimensions where experts might disagree.
    
    Topic: {debate_topic}
    Description: {debate_description}
    
    For each dimension, identify 2-3 possible stances.
    
    Example output format:
    {{
        "dimension_1": {{
            "name": "risk_tolerance",
            "stances": ["risk_averse", "balanced", "aggressive"]
        }},
        "dimension_2": {{
            "name": "timeline",
            "stances": ["immediate", "gradual", "long_term"]
        }},
        ...
    }}
    """
    
    dimensions = call_llm(prompt)
    return dimensions

def assign_positions(participants, dimensions):
    """
    Assign each participant a unique combination of stances.
    Ensures maximum diversity.
    """
    
    import itertools
    
    # Generate all possible stance combinations
    stance_combinations = list(itertools.product(*[d['stances'] for d in dimensions.values()]))
    
    # Assign different combinations to each agent
    for i, agent in enumerate(participants):
        agent.assigned_stances = stance_combinations[i % len(stance_combinations)]
        
        # Convert to natural language
        agent.position_description = f"""
        Your assigned perspective for this debate:
        {format_stances_naturally(agent.assigned_stances, dimensions)}
        
        You should advocate for this perspective (but can adjust if evidence strongly contradicts it).
        """
    
    return participants
```

---

### Step 3: Rejection Logic

```python
def validate_agent_message(message, agent, debate_history, round_number):
    """
    Multi-layer validation. Reject if fails any check.
    """
    
    rejections = []
    
    # Check 1: Similarity to recent messages
    similarity_check = check_message_originality(message, debate_history)
    if not similarity_check["approved"]:
        rejections.append(similarity_check["reason"])
    
    # Check 2: Banned phrases
    banned_phrases = ["I appreciate", "Great point", "I agree with", "Building on that"]
    for phrase in banned_phrases:
        if phrase.lower() in message.lower():
            rejections.append(f"Contains banned agreeable phrase: '{phrase}'")
    
    # Check 3: Questions in later rounds
    if round_number > 1 and "?" in message:
        question_count = message.count("?")
        if question_count > 1:
            rejections.append(f"Round {round_number} should focus on statements, not questions ({question_count} questions found)")
    
    # Check 4: Vague language
    vague_terms = ["consider", "think about", "we should", "it's important", "we need to evaluate"]
    vague_count = sum(1 for term in vague_terms if term in message.lower())
    if vague_count > 2:
        rejections.append(f"Too vague - contains {vague_count} non-specific phrases")
    
    # Check 5: Specificity requirement
    has_numbers = any(char.isdigit() for char in message)
    has_examples = "example" in message.lower() or "e.g." in message.lower()
    has_citations = "(" in message and ")" in message
    
    if not (has_numbers or has_examples or has_citations):
        rejections.append("Lacks specificity - no numbers, examples, or citations")
    
    # Check 6: Disagreement requirement (Round 2+)
    if round_number >= 2:
        disagreement_indicators = ["however", "but", "disagree", "challenge", "contrary", "instead", "alternatively"]
        has_disagreement = any(indicator in message.lower() for indicator in disagreement_indicators)
        
        if not has_disagreement:
            rejections.append("Must challenge or disagree with at least one previous point")
    
    if rejections:
        return {
            "approved": False,
            "rejections": rejections,
            "retry_instruction": generate_retry_instruction(rejections, round_number)
        }
    
    return {"approved": True}
```

---

### Step 4: Retry Instruction Generator

```python
def generate_retry_instruction(rejections, round_number):
    """
    Give agent specific guidance on what to fix.
    """
    
    instruction = f"""
    Your message was rejected for the following reasons:
    {chr(10).join(f"- {r}" for r in rejections)}
    
    For Round {round_number}, you should:
    """
    
    if round_number == 1:
        instruction += """
        - State your PRIMARY position clearly
        - Provide specific evidence (numbers, studies, examples)
        - Focus on YOUR perspective, not agreeing with others
        """
    elif round_number == 2:
        instruction += """
        - Identify a specific flaw in another agent's position
        - Provide counter-evidence or data
        - NO general statements - be specific and critical
        - Avoid questions - make assertions
        """
    elif round_number == 3:
        instruction += """
        - Address specific criticisms of your position
        - Provide additional evidence to defend your stance
        - Acknowledge valid points but explain why your approach is still superior
        - Refine your position based on new information
        """
    else:  # Round 4
        instruction += """
        - Provide a FINAL, ACTIONABLE recommendation
        - Include specific steps, protocols, or decisions
        - Must be concrete enough that someone could implement it
        - Explain why your approach is the best synthesis
        """
    
    return instruction
```

---

## 📊 EXAMPLE: How This Works for Different Topics

### Example 1: Medical Debate (Your Current Topic)
```python
Topic: "Best workout for asthma patient"

# Step 1: Extract dimensions
dimensions = {
    "risk_tolerance": ["safety_first", "balanced", "performance_focused"],
    "environment": ["indoor_only", "mixed", "outdoor_preferred"],
    "intensity": ["low", "moderate", "high"]
}

# Step 2: Assign positions
Medical Doctor: ["safety_first", "indoor_only", "low"]
  → "Advocate for conservative, indoor, low-intensity approach"

Fitness Expert: ["performance_focused", "mixed", "high"]
  → "Advocate for results-driven, varied environment, higher intensity"

Lifestyle Coach: ["balanced", "outdoor_preferred", "moderate"]
  → "Advocate for holistic, nature-based, sustainable approach"
```

### Example 2: Tech Policy Debate
```python
Topic: "Should we regulate AI development?"

# Step 1: Extract dimensions
dimensions = {
    "regulation_level": ["minimal", "moderate", "strict"],
    "enforcement": ["voluntary", "incentive_based", "mandatory"],
    "scope": ["national", "international"]
}

# Step 2: Assign positions
Tech CEO: ["minimal", "voluntary", "national"]
  → "Advocate for self-regulation and innovation freedom"

Policy Expert: ["strict", "mandatory", "international"]
  → "Advocate for strong global regulations"

Ethicist: ["moderate", "incentive_based", "international"]
  → "Advocate for balanced approach with global cooperation"
```

### Example 3: Climate Policy Debate
```python
Topic: "Best carbon reduction strategy"

# Step 1: Extract dimensions
dimensions = {
    "approach": ["technology", "regulation", "market"],
    "timeline": ["immediate", "decade", "gradual"],
    "cost": ["expensive_rapid", "balanced", "low_cost_slow"]
}

# Positions assigned automatically based on agent roles
```

---

## 🎯 BENEFITS OF THIS APPROACH

✅ **Topic-Agnostic**: Works for ANY debate without hardcoding

✅ **Scalable**: Add any number of participants, system adapts

✅ **Automatic**: Position assignment happens dynamically via LLM

✅ **Measurable**: Similarity scores, specificity metrics are quantifiable

✅ **Transparent**: Agents know their assigned perspective upfront

✅ **Flexible**: Agents can shift position if evidence warrants it

---

## 🔧 IMPLEMENTATION CHECKLIST

- [ ] 1. Add dimension extraction logic to debate initialization
- [ ] 2. Assign diverse positions to each participant
- [ ] 3. Update agent system prompt with universal rules
- [ ] 4. Add round-specific instructions
- [ ] 5. Implement similarity detection
- [ ] 6. Add banned phrase detection
- [ ] 7. Add vague language detection
- [ ] 8. Add disagreement requirement checker
- [ ] 9. Implement retry instruction generator
- [ ] 10. Test with 3 different debate topics

---

## 📈 EXPECTED OUTCOMES

### Before (Current):
- 17 messages
- 4 unique ideas
- 70%+ message similarity
- 0 specific recommendations

### After (With General Fix):
- 12-15 messages
- 15+ unique ideas
- <40% message similarity
- 3-5 specific, actionable recommendations

---

**This solution works for ANY debate topic with ANY participants!**

No hardcoding needed. Just structural rules + dynamic position assignment.
