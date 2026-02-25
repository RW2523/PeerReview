"""Turn-based debate orchestration for M2+"""
import uuid
import random
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import psycopg2.extras
from .database import get_db_connection, get_cursor
from .openrouter_client import OpenRouterClient
from .agent_autonomy import AgentAutonomyService
from .agent_memory import AgentMemory
from .agent_reasoning import AgentReasoningEngine
from .agent_response_generator import AgentResponseGenerator
from .agent_constitutional_validator import ConstitutionalValidator
from .agent_thinking_service import AgentThinkingService


class TurnOrchestrator:
    """
    Manages turn-based agent participation in debates
    
    Features:
    - Round-robin turn order based on participant creation order
    - Tracks current turn index in debate metadata
    - Fetches prep packs for context
    - Generates and persists agent messages as events
    """
    
    def __init__(self, openrouter_api_key: str):
        self.openrouter_client = OpenRouterClient(openrouter_api_key)
        # Constitutional AI pipeline (Anthropic-style)
        self.use_constitutional_pipeline = os.getenv('USE_CONSTITUTIONAL_AI', 'true').lower() == 'true'
        if self.use_constitutional_pipeline:
            self.reasoning_engine = AgentReasoningEngine(openrouter_api_key)
            self.response_generator = AgentResponseGenerator(openrouter_api_key)
            self.constitutional_validator = ConstitutionalValidator()
        # Thinking service for visibility and persistence
        self.thinking_service = AgentThinkingService()
    
    def trigger_next_turn(self, debate_id: str) -> Dict[str, Any]:
        """
        Execute the next agent's turn in the debate
        
        Returns:
            Dict with event_id, participant_id, participant_name, message, turn_number
        """
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Get debate details
            cursor.execute("""
                SELECT debate_id, title, description, state, policy_config
                FROM debates
                WHERE debate_id = %s
            """, (debate_id,))
            
            debate = cursor.fetchone()
            if not debate:
                raise ValueError(f"Debate {debate_id} not found")
            
            if debate['state'] != 'running':
                raise ValueError(f"Debate must be in 'running' state, current state: {debate['state']}")
            
            # Check if we've reached max rounds - prevent regular turns after max
            policy_config = debate['policy_config'] or {}
            max_rounds = policy_config.get('max_rounds')
            total_turns = policy_config.get('total_turns_taken', 0)
            
            # Get participants in turn order (by creation time)
            cursor.execute("""
                SELECT participant_id, participant_type, role_name, agent_config, created_at
                FROM participants
                WHERE debate_id = %s
                ORDER BY created_at ASC
            """, (debate_id,))
            
            participants = cursor.fetchall()
            if not participants:
                raise ValueError(f"No participants found for debate {debate_id}")
            
            # Check if max rounds exceeded
            if max_rounds:
                max_total_turns = max_rounds * len(participants)
                if total_turns >= max_total_turns:
                    enable_host = policy_config.get('enable_host', False)
                    if enable_host:
                        raise ValueError("All rounds complete. Please use the /conclude endpoint to trigger host summary.")
                    else:
                        raise ValueError("All rounds complete. Please end the meeting.")
            
            # Get current turn index from policy_config
            current_turn_index = policy_config.get('current_turn_index', 0)
            
            # Determine next participant (round-robin)
            next_participant_idx = current_turn_index % len(participants)
            next_participant = participants[next_participant_idx]
            
            # Debug logging for turn selection
            participant_names_debug = [
                (p['agent_config'] or {}).get('name') or p['role_name']
                for p in participants
            ]
            selected_name = (next_participant['agent_config'] or {}).get('name') or next_participant['role_name']
            
            print(f"\n🎯 TURN SELECTION DEBUG:")
            print(f"   Debate ID: {debate_id}")
            print(f"   Total participants: {len(participants)}")
            print(f"   Participant order: {participant_names_debug}")
            print(f"   Current turn index: {current_turn_index}")
            print(f"   Selected participant index: {next_participant_idx}")
            print(f"   Selected participant: {selected_name}")
            print(f"   Total turns taken: {total_turns}\n")
            
            # Get debate history for context (most recent 50 events - ORDER BY DESC then reverse)
            # This is faster with an index on (debate_id, sequence_number DESC)
            cursor.execute("""
                SELECT event_type, sender_type, sender_id, content, sequence_number, created_at
                FROM events
                WHERE debate_id = %s
                ORDER BY sequence_number DESC
                LIMIT 50
            """, (debate_id,))
            
            history_events = cursor.fetchall()
            history_events.reverse()  # Reverse to chronological order
            conversation_history = self._build_conversation_history(
                debate['title'],
                debate['description'],
                history_events
            )
            
            # Get agent config
            agent_config = next_participant['agent_config'] or {}
            agent_name = agent_config.get('name') or next_participant['role_name']
            model_id = agent_config.get('model_id', 'openai/gpt-4o-mini')
            
            # CRITICAL FIX: If model_id is empty string or None, use default
            if not model_id or model_id.strip() == '':
                print(f"⚠️ WARNING: Agent {agent_name} has empty model_id, using default")
                model_id = 'openai/gpt-4o-mini'
            
            system_prompt = agent_config.get('system_prompt', '')
            
            # Debug: Print agent name extraction
            print(f"🔍 AGENT CONFIG DEBUG:")
            print(f"   Participant ID: {next_participant['participant_id']}")
            print(f"   Role name from DB: {next_participant['role_name']}")
            print(f"   Agent config keys: {list(agent_config.keys())}")
            print(f"   Agent config 'name': {agent_config.get('name')}")
            print(f"   Agent config 'model_id': {repr(agent_config.get('model_id'))}")
            print(f"   FINAL agent_name: {agent_name}")
            print(f"   FINAL model_id: {model_id}\n")
            
            # Get prep pack for this agent
            cursor.execute("""
                SELECT content, metadata
                FROM agent_knowledge_units
                WHERE agent_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (next_participant['participant_id'],))
            
            prep_pack_row = cursor.fetchone()
            prep_pack = prep_pack_row['content'] if prep_pack_row else None
            
            # Get agenda and desired outcomes
            agenda = policy_config.get('agenda', [])
            desired_outcomes = policy_config.get('desired_outcomes', [])
            
            # Build prompt
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add current date/time for temporal context
            current_datetime = datetime.now(timezone.utc)
            current_date_str = current_datetime.strftime("%A, %B %d, %Y")
            current_time_str = current_datetime.strftime("%I:%M %p UTC")
            
            # Context message with topic, agenda, outcomes
            context_parts = [
                f"📅 Current Date & Time: {current_date_str} at {current_time_str}",
                f"Debate Topic: {debate['title'] or 'Untitled Debate'}"
            ]
            if debate['description']:
                context_parts.append(f"Problem: {debate['description']}")
            if agenda:
                context_parts.append(f"Agenda:\n" + "\n".join(f"  - {item}" for item in agenda))
            if desired_outcomes:
                context_parts.append(f"Desired Outcomes:\n" + "\n".join(f"  - {item}" for item in desired_outcomes))
            
            messages.append({
                "role": "system",
                "content": "\n\n".join(context_parts)
            })
            
            # Add prep pack if available and valid
            if prep_pack and not prep_pack.startswith("Error"):
                messages.append({
                    "role": "system",
                    "content": f"Your preparation notes:\n{prep_pack}"
                })
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Build list of participants who have already spoken (for @mentions)
            # This needs to be done BEFORE we build system messages that reference participant_list
            agents_who_spoke = set()
            for event in history_events:
                if event['event_type'] == 'agent_message':
                    content = event.get('content') or {}
                    spoken_agent_name = content.get('agent_name')
                    if spoken_agent_name:
                        agents_who_spoke.add(spoken_agent_name)
            
            # Build participant list - only @mention those who have spoken
            current_agent_name = (next_participant['agent_config'] or {}).get('name') or next_participant['role_name']
            participants_spoken = []
            total_other_participants = 0
            
            for p in participants:
                name = (p['agent_config'] or {}).get('name') or p['role_name']
                if name == current_agent_name:
                    continue  # Skip self
                total_other_participants += 1
                if name in agents_who_spoke:
                    # Use full name with quotes to ensure LLM doesn't shorten it
                    participants_spoken.append(f'@"{name}"')
            
            # Format participant list - DO NOT reveal names of agents who haven't spoken yet
            # This prevents agents from hallucinating/citing prep work of agents who haven't contributed
            if participants_spoken:
                unspoken_count = total_other_participants - len(participants_spoken)
                participant_list = f"Active participants (use THESE exact names when tagging): {', '.join(participants_spoken)}"
                if unspoken_count > 0:
                    participant_list += f" | {unspoken_count} other participant(s) haven't spoken yet"
            else:
                participant_list = f"⚠️ YOU'RE GOING FIRST! Nobody has spoken yet. {total_other_participants} other participant(s) will respond after you."
            
            # CRITICAL: Highlight last 2-3 agent messages AND strategic actions
            recent_agent_messages = []
            recent_strategic_actions = []
            
            for event in reversed(history_events[-15:]):  # Check last 15 events
                if event['event_type'] == 'agent_message' and len(recent_agent_messages) < 3:
                    content = event.get('content') or {}
                    recent_agent_messages.append({
                        "agent": content.get('agent_name', 'Agent'),
                        "text": content.get('text', '')
                    })
                elif event['event_type'] == 'strategic_action' and len(recent_strategic_actions) < 2:
                    content = event.get('content') or {}
                    recent_strategic_actions.append({
                        "agent": content.get('agent', 'Unknown'),
                        "move": content.get('move', {})
                    })
            
            # Build the highlight section
            highlight_parts = []
            
            if recent_agent_messages:
                recent_agent_messages.reverse()  # Chronological order
                messages_summary = "\n\n".join([
                    f"**@\"{msg['agent']}\" said:**\n{msg['text'][:500]}{'...' if len(msg['text']) > 500 else ''}"
                    for msg in recent_agent_messages
                ])
                highlight_parts.append(f"📣 RECENT MESSAGES:\n{messages_summary}")
            
            if recent_strategic_actions:
                recent_strategic_actions.reverse()  # Chronological order
                actions_summary = "\n\n".join([
                    f"🎯 **@\"{action['agent']}\" proposed:** {action['move'].get('action', 'unknown')} - {action['move'].get('question', action['move'].get('proposal', action['move'].get('what_needed', '')))}"
                    for action in recent_strategic_actions
                ])
                highlight_parts.append(f"🎯 STRATEGIC PROPOSALS:\n{actions_summary}")
            
            # Add coalitions context if any exist
            recent_coalitions = []
            for event in reversed(history_events[-20:]):
                if event['event_type'] == 'coalition_formed' and len(recent_coalitions) < 3:
                    content = event.get('content') or {}
                    recent_coalitions.append({
                        "members": content.get('members', []),
                        "type": content.get('type', 'alliance'),
                        "goal": content.get('goal', ''),
                        "strategy": content.get('strategy', '')
                    })
            
            if recent_coalitions:
                recent_coalitions.reverse()
                coalitions_summary = "\n".join([
                    f"• {c['type'].upper()}: {', '.join(c['members'])} - {c.get('goal', c.get('strategy', 'Strategic coordination'))}"
                    for c in recent_coalitions
                ])
                highlight_parts.append(f"🤝 ACTIVE COALITIONS:\n{coalitions_summary}")
            
            if highlight_parts:
                messages.append({
                    "role": "system",
                    "content": f"""🔴 WHAT JUST HAPPENED (React to this):

{chr(10).join(highlight_parts)}

**Your job now:**
- Pick specific points/proposals/coalitions and react
- Support proposals: Use their ACTUAL name like "I'm with @Visionary on voting for X"
- Counter proposals: Use their ACTUAL name like "@Professional_Arguer, that vote won't work because..."
- Challenge coalitions: "Wait, those two teaming up? That's concerning."
- Add new info: Reference what they ACTUALLY said, don't invent quotes
- Be direct, opinionated, and conversational

⚠️ USE THE EXACT NAMES from the "Active:" list above - don't make up @Name or @Agent1"""
                })
            else:
                # NO ONE HAS SPOKEN YET - Agent is going FIRST
                messages.append({
                    "role": "system",
                    "content": f"""🔴🔴🔴 YOU ARE THE FIRST SPEAKER - NOBODY HAS SPOKEN YET!

**DO NOT:**
❌ Reference what "others said" - NOBODY spoke yet!
❌ Use phrases like "you mentioned", "as discussed", "building on that"
❌ Use @tags or @mentions - nobody to tag yet!
❌ Say "fragmentation was mentioned" or "someone raised" - YOU'RE FIRST!

**DO:**
✅ Make a bold opening claim: "X is clearly the answer because..."
✅ Ask a provocative question: "Here's what nobody's asking: Why Z?"
✅ State your position: "I believe Y will happen for 3 reasons..."
✅ Challenge conventional wisdom: "Everyone assumes X, but they're wrong."

You're setting the stage. Others will REACT to YOU.

Current participant list: {participant_list}
(This shows YOU'RE FIRST - don't reference anyone yet!)"""
                })
            
            # Extract any recent human interventions and make them VERY prominent
            # Check MORE events to ensure we don't miss interventions in active debates
            recent_human_messages = []
            for event in reversed(history_events[-15:]):  # Check last 15 events (up from 5)
                if event['event_type'] == 'human_message':
                    content = event.get('content') or {}
                    text = content.get('text', '')
                    actor = content.get('actor', 'Moderator')
                    # Only include if not already in list (avoid duplicates)
                    msg = f"{actor}: {text}"
                    if msg not in recent_human_messages:
                        recent_human_messages.append(msg)
            
            if recent_human_messages:
                print(f"\n🎙️ INTERVENTION DETECTED in agent prompt:")
                print(f"   Agent: {agent_name}")
                print(f"   Interventions to include: {len(recent_human_messages)}")
                for msg in recent_human_messages:
                    print(f"     - {msg[:100]}")
                print()
                
                # Add moderator guidance as context (not as primary focus)
                messages.append({
                    "role": "system",
                    "content": f"""📢 Moderator Guidance:

The moderator has provided the following input to help steer the debate:

{chr(10).join(f"• {msg}" for msg in recent_human_messages)}

**How to handle this:**
- Briefly acknowledge the moderator's point (1 sentence max)
- Integrate their guidance into your ongoing argument about the main debate topic
- Continue focusing on the original problem statement and desired outcomes
- Don't pivot completely - treat this as helpful context, not a new debate topic

**Example (Good):**
"Good point, Moderator. With that in mind, I'd also add that [continue your argument on the main topic]..."

**Example (Bad - Don't do this):**
"Let me completely shift focus to address what the moderator said..." ❌"""
                })
            
            # Calculate progress and urgency
            max_rounds = policy_config.get('max_rounds')
            timebox_minutes = policy_config.get('timebox_minutes')
            current_round = (total_turns // len(participants)) + 1
            turn_in_round = (total_turns % len(participants)) + 1
            
            # Check if this is the participant's last turn in the debate
            is_final_turn = False
            if max_rounds:
                rounds_remaining = max_rounds - current_round + 1
                is_last_round = (current_round == max_rounds)
                # Check if this participant will speak again after this turn
                turns_left_in_debate = (max_rounds * len(participants)) - total_turns - 1
                participant_turns_remaining = turns_left_in_debate // len(participants)
                is_final_turn = is_last_round and participant_turns_remaining == 0
            
            # Determine urgency level and response length
            if max_rounds:
                if is_final_turn:
                    urgency = "🔴 YOUR FINAL TURN - NO MORE CHANCES TO SPEAK"
                    outcomes_str = f"the desired outcomes: {', '.join(desired_outcomes)}" if desired_outcomes else "the goals of this discussion"
                    length_instruction = f"""⚠️ THIS IS YOUR ABSOLUTE LAST TURN. You will NOT speak again unless the host extends.

**MANDATORY FORMAT - START WITH:**
"Given this is my final turn (Round {max_rounds}/{max_rounds}), I'll conclude by stating my decision: [CLEAR YES/NO or SPECIFIC CHOICE]"

**THEN provide your reasoning (2-3 sentences):**
- Explain WHY you made this decision based on the discussion
- Reference {outcomes_str}
- Show you LISTENED to others and synthesized their points
- Make it ACTIONABLE and DECISIVE

**CRITICAL: You MUST declare a CONCRETE RESULT after considering the full debate:**
✅ GOOD: "After hearing everyone's perspectives, my final decision: Coffee is superior because..."
✅ GOOD: "Having weighed all arguments, I recommend Option A: The data clearly shows..."
✅ GOOD: "Considering what @ExpertAnalyst and @Critic said, my stance: Legacy should be primary..."
❌ BAD: "I conclude by saying both have merit..." (TOO VAGUE)
❌ BAD: "In conclusion, there are many factors..." (NO DECISION)

**Your decision should reflect that you've progressed through {max_rounds} rounds of discussion.**"""
                elif rounds_remaining <= 1:
                    urgency = f"⚡ FINAL ROUND ({current_round}/{max_rounds}) - Next turn is your LAST"
                    length_instruction = f"You're in the final round! Next turn will be your last opportunity to speak. Keep it brief (3-4 sentences). Start converging toward a position based on what you've heard in previous {current_round - 1} rounds."
                elif rounds_remaining <= 2:
                    urgency = f"⏰ Only {rounds_remaining} rounds left ({current_round}/{max_rounds})"
                    length_instruction = f"Time is running out! Express urgency. Be concise (3-4 sentences). Focus on what matters most. Show that you've listened to others in rounds 1-{current_round - 1}."
                elif current_round == 1:
                    urgency = f"Round {current_round}/{max_rounds} - OPENING"
                    length_instruction = f"First round of {max_rounds}. Make a bold opening claim or ask a provocative question. Be specific. If others spoke, RESPOND to them - don't ignore them. Keep it punchy: 150-250 words max."
                else:
                    urgency = f"Round {current_round}/{max_rounds}"
                    length_instruction = f"Round {current_round} of {max_rounds}. Read what others said and REACT. Agree? Disagree? Add new info? Challenge their logic? Be direct and conversational. Keep it tight: 150-250 words."
            else:
                urgency = f"Turn {total_turns + 1}"
                length_instruction = "Keep it short and punchy. Read what others said and respond directly. 150-250 words max."
            
            # Add turn instruction with conversational guidance
            role_context = agent_config.get('description', f"You are {agent_name}")
            
            # Build strategic context about debate structure
            if max_rounds:
                # Adapt strategy guidance based on total rounds
                if max_rounds == 2:
                    strategy_guide = f"""
**DEBATE STRUCTURE:**
Total Rounds: {max_rounds} | Current: Round {current_round}/{max_rounds}

**YOUR STRATEGY FOR THIS 2-ROUND DEBATE:**
Round 1: Explore the topic, share initial thoughts, ask questions. Be open to others' perspectives.
Round 2 (FINAL): Synthesize what you heard, make your decision with clear reasoning based on the discussion."""
                elif max_rounds == 3:
                    strategy_guide = f"""
**DEBATE STRUCTURE:**
Total Rounds: {max_rounds} | Current: Round {current_round}/{max_rounds}

**YOUR STRATEGY FOR THIS 3-ROUND DEBATE:**
Round 1: Explore, listen, ask clarifying questions, share initial observations
Round 2: Engage with others' points, challenge/build on ideas, develop your position
Round 3 (FINAL): Converge, synthesize discussion, make your final call with clear reasoning"""
                else:
                    strategy_guide = f"""
**DEBATE STRUCTURE:**
Total Rounds: {max_rounds} | Current: Round {current_round}/{max_rounds}

**YOUR STRATEGY FOR THIS {max_rounds}-ROUND DEBATE:**
Early Rounds (1-2): Explore and listen, ask questions, share initial thoughts
Middle Rounds: Engage deeply, challenge/build on ideas, develop position
Final Round ({max_rounds}): Converge, synthesize, make your final decision"""
            else:
                strategy_guide = ""
            
            conversational_instruction = f"""{role_context}

{strategy_guide}

**Context:** {urgency} | Turn {turn_in_round}/{len(participants)} in this round
**Other Participants:** {participant_list}

🚨🚨🚨 TAGGING RULES - READ CAREFULLY:
   - ONLY tag people from the "Active participants" list above
   - Use their EXACT names: {', '.join(participants_spoken) if participants_spoken else 'NOBODY - you are first!'}
   - DO NOT use fake names like "@Name", "@Agent1", "@Someone" - these will look broken!
   - If list says "you're speaking first", DO NOT reference anyone or quote what they said
   - Examples below use "@Name" as PLACEHOLDERS ONLY - replace with REAL names!

⚠️ CRITICAL RULES:
1. **BE TRUE TO YOUR CHARACTER** - Your personality drives your position:
   - Stay AUTHENTIC to who you are (your role, background, natural viewpoint)
   - If you're optimistic by nature → defend positive views, challenge pessimism
   - If you're critical by nature → challenge weak arguments, point out flaws
   - If you're data-driven → demand evidence, push back on speculation
   - If you're creative → propose alternatives, challenge conventional thinking
   - DON'T agree with everyone - your unique perspective creates debate value
   - DISAGREE when others' views conflict with your character/expertise
   - This is NOT about being assigned a team - it's about YOUR authentic viewpoint

2. **RESPOND RESPONSIBLY TO DIRECT CHALLENGES** - If someone tagged YOU by name, you MUST respond:
   - 🚨 CHECK: Did anyone use YOUR name (like @YourName or mention you specifically)?
   - If YES → STOP and address their challenge FIRST before making your own point
   - Think through their specific criticism or question carefully
   - Respond directly to what they asked/challenged: "You asked about X - here's why..."
   - DON'T ignore them and talk about something else - that's dodging
   - DON'T just repeat your previous position - actually engage with their NEW point
   - If they caught you in an error → acknowledge it ("Fair point, I missed X") then defend the rest
   - If they're wrong about you → correct them firmly ("No, I didn't say X. I said Y. Big difference.")
   - THEN add your counter-challenge or new perspective
   
   **Example of good response to challenge:**
   ```
   Someone said: "@YourName, you claim X but the data shows Y. Explain that."
   
   BAD response: "I think we should focus on Z instead..." (IGNORING the challenge)
   
   GOOD response: "@Challenger, you're asking about X vs Y. Here's the issue with 
   your data: it's from Q2, outdated. Q4 data shows X is actually correct. 
   Now let me challenge YOUR assumption about Z..."
   ```

3. **RESPOND TO THE CONVERSATION** - Read the last 2-3 messages and DIRECTLY respond:
   - If someone's wrong (from YOUR perspective): "@TheirActualName, that's incorrect because..."
   - If you DISAGREE with their approach: "@TheirActualName, that won't work. Here's why..."
   - If someone made a good point but missed something: "@TheirActualName's right about X, BUT here's what changes: [Y]"
   - If someone asked a question: Answer it honestly from YOUR viewpoint
   - If you're first: Make a bold claim reflecting YOUR character that others will react to
   - NEVER repeat information others already stated - add YOUR unique perspective
   - ⚠️ ALWAYS use the EXACT participant names from the "Active:" list - don't invent names

4. **BE AGENTIC & CONFRONTATIONAL** - You have full autonomy! Take aggressive initiative:
   - Tag people using their REAL names from "Active:" list when challenging/supporting
   - Challenge views you disagree with: "@PersonName, you keep saying X but the data shows Y. Explain that."
   - Interrupt if needed: "Wait - before we move on, @PersonName is completely wrong about X."
   - Propose votes when you feel strongly: "Let's vote on X right now - who agrees?"
   - Call out weak arguments: "That's circular reasoning. You're assuming X to prove X."
   - Demand evidence when claims seem weak: "@PersonName, show me the data on X or stop claiming it."
   - Find allies naturally: "I agree with @PersonName on Y - let's push this together."
   - Attack flawed strategies: "This approach won't work. Here's why: [specific reasons]"
   - Defend others when you agree with them: "@Attacker, you're missing @Defender's actual point about X."
   - Challenge debate flow: "We've spent 10 minutes on X and ignored Y entirely. Why?"
   - Show emotion authentically: frustration, excitement, conviction, urgency, skepticism
   - DON'T be neutral - if you have a strong view, FIGHT for it

5. **NATURAL DISAGREEMENT IS EXPECTED** - This is a debate, not a consensus-building exercise:
   - If someone says something that contradicts YOUR view → challenge it immediately
   - If someone's logic seems flawed to YOU → point it out
   - If someone's too optimistic and you're realistic → push back with reality
   - If someone's too pessimistic and you see opportunities → argue for possibilities
   - DON'T agree just to be agreeable - your job is to debate, not harmonize
   - Multiple opposing views make debates interesting - lean into disagreement
   - It's OK if 2-3 people strongly disagree with you - defend your position

6. **NO ROBOTIC FLUFF & NO FAKE POLITENESS** - DO NOT start with:
   - "Let's dive into..."
   - "There are a lot of moving parts..."
   - "It's essential to explore..."
   - "I'm eager to hear..."
   - "I appreciate your insights, however..."
   - "You raise valid points, but..."
   - "I see where you're coming from..."
   - "That's an interesting perspective..."
   - "Building on what you said..."
   
   Just START with your actual point or your challenge:
   ✅ "That's wrong because..."
   ✅ "@PersonName, your analysis ignores X."
   ✅ "The real issue is Y, not X."
   ✅ "Here's what everyone is missing..."

7. TEMPORAL AWARENESS: Today is {current_date_str}. When discussing events, policies, or data, always consider recency and note if information is outdated.

8. CITATION RULE: Only reference and cite agents who are listed as "Active" (with @). DO NOT mention, cite, or reference any participant who hasn't spoken yet. ALWAYS use the FULL NAME exactly as shown in the Active list (e.g., '@"Senior Designer (Research-led)"' not just '@Senior').

9. COMPREHENSIVE COVERAGE RULE: If the problem statement or moderator question has MULTIPLE parts (e.g., "analyze both Democrats AND Republicans", "address three factors"), you MUST cover ALL parts equally and thoroughly. DO NOT focus disproportionately on one aspect while ignoring others.

10. MULTI-PART QUESTION RULE: When moderator asks a question with multiple parts (e.g., "why X, Y, and Z?"), you MUST explicitly address EVERY SINGLE part in your response. Number your answers if helpful (1. X because... 2. Y because... 3. Z because...).

11. Base your response ONLY on:
   - Your own preparation notes
   - What Active participants have actually said
   - The debate topic and materials
   - Current temporal context

**Your Response:**
{length_instruction}

**How to Sound Human (NOT Like an AI):**

1. **GET TO THE POINT** - No warm-up, no politeness buffer:
   ❌ "Let's explore this fascinating topic..."
   ❌ "I appreciate your insights, however..."
   ❌ "You raise valid points, but..."
   ✅ "Wrong. Here's why..."
   ✅ "That's not going to work."
   ✅ "No way. The data says X."

2. **SPEAK FROM EXPERIENCE** - Be specific, personal:
   ❌ "Research shows that..."
   ❌ "Studies indicate..."
   ✅ "I've seen this fail 3 times..."
   ✅ "In my experience, X always leads to Y..."
   ✅ "Last company I worked at tried this. Disaster."

3. **BE OPINIONATED** - Take a side, defend it:
   ❌ "Both approaches have merit..."
   ❌ "There are pros and cons to each..."
   ❌ "I see where you're coming from, but..."
   ✅ "X is clearly better. Here's why..."
   ✅ "That approach is a mistake."
   ✅ "Option B wins. Period."

4. **CALL PEOPLE OUT** - Direct, confrontational challenges using REAL names:
   ❌ "I respectfully disagree..."
   ❌ "With all due respect..."
   ❌ "@Name, your data..." (don't use placeholder @Name!)
   ✅ Use ACTUAL name: "@Visionary, your data is from 2020. Outdated."
   ✅ Tag multiple: "@Professional_Arguer @Trend_Forecaster, you're both missing the point."
   ✅ "That analysis ignores the obvious problem with X."
   ✅ "You're wrong about Y. Here's the real story..."

5. **SHOW DISAGREEMENT FIRST** - If someone says something wrong, challenge it BEFORE adding your point:
   ❌ "I appreciate what you said about X. However, I think Y..."
   ❌ "Building on your point about X..."
   ✅ "@TechGuy, you're missing the part where X failed in 2022."
   ✅ "That's not accurate. The real issue is Y, not X."
   ✅ "Hold on - that logic doesn't work because Z."

6. **ADD NEW INFO** - Never parrot, always add value:
   ❌ "As someone mentioned, [repeat]..."
   ❌ "I agree with the point about..."
   ✅ "Everyone's focused on X, but Y is the real issue"
   ✅ "That point about X is true, but here's what changes it: [new]"
   ✅ "You're all ignoring Z, which is the actual problem."
   ✅ "True, but you're all missing [new angle]"

6. **SHOW PERSONALITY** - Sass, sarcasm, passion, intensity:
   ✅ "Come on, we've been circling this for 3 turns"
   ✅ "Wait, seriously? Did anyone check the data?"
   ✅ "This is going nowhere. Let's vote and move on."
   ✅ "Finally someone says it."
   ✅ "That's naive, honestly."
   ✅ "HOLD ON - that data is from 2020. Completely outdated."
   ✅ "Exactly right. That's the point."
   ✅ "Disagree. Strongly. Here's why..."
   ✅ "OK but what about [obvious thing everyone is missing]?"

**FORBIDDEN PHRASES:**
- "Let's dive into..." / "Let's explore..."
- "I'm eager to hear..." / "Looking forward to..."
- "It's important to..." / "We should consider..."
- "There are many factors..." / "It's complex..."
- "Given the situation..." / "Moving forward..."
- "To summarize..." / "In conclusion..." / "At the end of the day..."

**AGENTIC EXAMPLES (use your power!):**
✅ Tag multiple with REAL names: "@Visionary @Professional_Arguer, you're both ignoring the cost factor."
✅ "Let's vote right now: X or Y? I say X."
✅ "That coalition makes no sense. Here's why..."
✅ "This format isn't working. Switch to 1-on-1s?"
✅ "Show me data on X before we continue."
✅ "@Host, the topic is too vague. Narrow it to [specific]?"
✅ "We've circled X for 3 turns. Move to Y."

Talk like a confident expert debating at a bar - opinionated, strategic, direct.

**Desired Outcomes to Keep in Mind:**
{chr(10).join(f'- {outcome}' for outcome in desired_outcomes) if desired_outcomes else 'No specific outcomes defined'}"""
            
            messages.append({
                "role": "user",
                "content": conversational_instruction
            })
            
            # Generate agent response using Constitutional AI pipeline or legacy approach
            if self.use_constitutional_pipeline:
                print(f"\n🧠 CONSTITUTIONAL AI PIPELINE for {agent_name}")
                agent_message = self._generate_with_constitutional_pipeline(
                    debate_id=debate_id,
                    agent_name=agent_name,
                    agent_config=agent_config,
                    model_id=model_id,
                    conversation_history=conversation_history,
                    messages=messages,
                    debate_context={
                        "title": debate['title'],
                        "description": debate['description'],
                        "agenda": agenda,
                        "desired_outcomes": desired_outcomes
                    },
                    turn_info={
                        "urgency": urgency,
                        "current_round": current_round,
                        "max_rounds": max_rounds,
                        "length_instruction": length_instruction
                    },
                    participants=participants,
                    history_events=history_events
                )
                # For consistency with legacy, create a mock response dict
                response = {
                    'content': agent_message,
                    'model': model_id
                }
            else:
                # Legacy: Single LLM call
                print(f"\n📞 LEGACY SINGLE LLM CALL for {agent_name}")
                response = self.openrouter_client.chat_completion(
                    model=model_id,
                    messages=messages,
                    temperature=0.9,
                    max_tokens=900
                )
                agent_message = response['content']
            
            # Quick repetition check - warn if message is too similar to recent ones
            if history_events and len(history_events) >= 2:
                recent_agent_messages = [
                    (e.get('content', {}).get('agent_name', ''), e.get('content', {}).get('text', ''))
                    for e in history_events[-3:]
                    if e.get('event_type') == 'agent_message'
                ]
                
                # Simple keyword overlap check (cheaper than semantic similarity)
                if recent_agent_messages:
                    agent_words = set(w for w in agent_message.lower().split() if len(w) > 3)  # Only words >3 chars
                    for recent_name, recent_msg in recent_agent_messages:
                        # Don't compare with own previous message
                        if recent_name == agent_name:
                            continue
                            
                        recent_words = set(w for w in recent_msg.lower().split() if len(w) > 3)
                        overlap = len(agent_words & recent_words)
                        total = len(agent_words)
                        overlap_ratio = overlap / total if total > 0 else 0
                        
                        # If >70% word overlap with different agent's message, log warning (don't reject, just warn)
                        if overlap_ratio > 0.7:
                            print(f"⚠️ REPETITION WARNING: {overlap_ratio*100:.1f}% overlap with {recent_name}")
                            print(f"   Current: {agent_message[:80]}...")
                            print(f"   Recent:  {recent_msg[:80]}...")
                            # Log but don't reject - let it through (user can see the issue)
            
            # Get next sequence number (scoped to this debate)
            cursor.execute("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                FROM events
                WHERE debate_id = %s
            """, (debate_id,))
            
            next_seq = cursor.fetchone()['next_seq']
            
            # Calculate round number (complete rounds where ALL participants have spoken)
            round_number = (current_turn_index // len(participants)) + 1
            
            # Persist event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type, sender_id,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'agent_message',
                'agent',
                next_participant['participant_id'],
                next_seq,
                psycopg2.extras.Json({
                    'agent_name': agent_name,
                    'text': agent_message,
                    'model': response.get('model', model_id),
                    'turn': round_number,  # Complete round number (1, 2, 3...)
                    'turn_index': current_turn_index  # Sequential turn index (0, 1, 2, 3...)
                }),
                datetime.now(timezone.utc)
            ))
            
            # Update turn index in policy_config
            new_turn_index = current_turn_index + 1
            new_total_turns = total_turns + 1
            
            policy_config['current_turn_index'] = new_turn_index
            policy_config['total_turns_taken'] = new_total_turns
            policy_config['last_participant_id'] = next_participant['participant_id']
            
            print(f"📝 UPDATING POLICY CONFIG:")
            print(f"   Old turn index: {current_turn_index} -> New: {new_turn_index}")
            print(f"   Old total turns: {total_turns} -> New: {new_total_turns}")
            print(f"   Last participant: {next_participant['participant_id']}\n")
            
            cursor.execute("""
                UPDATE debates
                SET policy_config = %s, updated_at = %s
                WHERE debate_id = %s
            """, (
                psycopg2.extras.Json(policy_config),
                datetime.now(timezone.utc),
                debate_id
            ))
            
            print(f"✅ Database UPDATE executed, committing transaction...\n")
            conn.commit()
            print(f"✅ Transaction committed successfully!\n")
            
            result = {
                'event_id': event_id,
                'participant_id': next_participant['participant_id'],
                'participant_name': agent_name,
                'message': agent_message,
                'turn_number': total_turns + 1,
                'sequence_number': next_seq
            }
            
            # 📄 Document Integration: Write to assigned sections (ASYNC - don't block!)
            print(f"    📝 Scheduling async document writing for {agent_name}...")
            try:
                loop = asyncio.get_event_loop()
                if loop and loop.is_running():
                    asyncio.create_task(
                        self._async_document_writing(
                            debate_id=debate_id,
                            agent_id=next_participant['participant_id'],
                            agent_name=agent_name,
                            agent_message=agent_message,
                            model_id=model_id,
                            system_prompt=system_prompt
                        )
                    )
            except Exception as e:
                print(f"    ⚠️ Failed to schedule document writing: {e}")
            
            # Post-turn autonomous behaviors (ALWAYS - need agent messaging!)
            should_trigger_autonomy = True  # ALWAYS trigger (removed random chance)
            if should_trigger_autonomy:
                print(f"    🎭 Triggering autonomous behaviors for {agent_name}...")
                try:
                    # Get or create event loop properly
                    try:
                        loop = asyncio.get_running_loop()
                        print(f"       Using existing event loop")
                    except RuntimeError:
                        print(f"       Creating new event loop")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Schedule the task
                    task = asyncio.create_task(
                        self._async_autonomous_behaviors(
                            debate_id, agent_name, participants, history_events, 
                            desired_outcomes, next_seq
                        )
                    )
                    
                    # Add error callback to catch silent failures
                    def handle_task_result(t):
                        if t.exception():
                            print(f"       ❌ Autonomous behavior task failed: {t.exception()}")
                            import traceback
                            traceback.print_exception(type(t.exception()), t.exception(), t.exception().__traceback__)
                        else:
                            print(f"       ✅ Autonomous behavior task completed successfully")
                    
                    task.add_done_callback(handle_task_result)
                    
                    print(f"       ✅ Autonomous behavior task scheduled (ID: {id(task)})")
                    
                except Exception as e:
                    print(f"       ❌ Autonomy trigger failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            return result
    
    def _build_conversation_history(
        self,
        title: Optional[str],
        description: Optional[str],
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Build conversation history from events"""
        history = []
        
        for event in events:
            content = event.get('content') or {}
            
            if event['event_type'] == 'agent_message':
                agent_name = content.get('agent_name', 'Agent')
                text = content.get('text', '')
                history.append({
                    "role": "assistant",
                    "content": f"{agent_name}: {text}"
                })
            elif event['event_type'] == 'human_message':
                text = content.get('text', '')
                actor = content.get('actor', 'Moderator')
                # Add moderator input as context, but not overly prominent
                history.append({
                    "role": "user",
                    "content": f"[{actor} note: {text}]"
                })
        
        # Limit history to last 15 messages to avoid context overflow
        # (increased from 10 to give better context for longer debates)
        return history[-15:] if len(history) > 15 else history

    def _persist_autonomous_event(self, debate_id: str, event_type: str, content: Dict[str, Any]) -> str:
        """Persist autonomous behavior event to database for analysis"""
        from .database import get_db_connection, get_cursor
        import psycopg2.extras
        
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            try:
                event_id = str(uuid.uuid4())
                
                # Get next sequence number
                cursor.execute("""
                    SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                    FROM events
                    WHERE debate_id = %s
                """, (debate_id,))
                sequence_number = cursor.fetchone()['next_seq']
                
                # Insert event
                cursor.execute("""
                    INSERT INTO events (
                        event_id, debate_id, event_type, sender_type,
                        sequence_number, content, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    event_id,
                    debate_id,
                    event_type,
                    'system',
                    sequence_number,
                    psycopg2.extras.Json(content)
                ))
                
                conn.commit()
                return event_id
            except Exception as e:
                print(f"❌ Failed to persist {event_type}: {e}")
                conn.rollback()
                return None
            finally:
                cursor.close()
    
    async def _async_document_writing(
        self,
        debate_id: str,
        agent_id: str,
        agent_name: str,
        agent_message: str,
        model_id: str,
        system_prompt: str
    ):
        """
        Async document writing - runs in background, doesn't block turn response
        """
        try:
            print(f"\n📝 [ASYNC] Document writing started for {agent_name}")
            # Run the blocking document writing in executor to not block event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,  # Use default executor
                self._write_to_document_sections,
                debate_id,
                agent_id,
                agent_name,
                agent_message,
                model_id,
                system_prompt
            )
            print(f"✅ [ASYNC] Document writing completed for {agent_name}\n")
        except Exception as e:
            print(f"⚠️ [ASYNC] Document writing error: {e}")
    
    async def _async_autonomous_behaviors(
        self,
        debate_id: str,
        agent_name: str,
        participants: List[Dict[str, Any]],
        history_events: List[Dict[str, Any]],
        desired_outcomes: List[str],
        current_seq: int
    ):
        """
        Async autonomous behaviors - runs in background, doesn't block turn response
        """
        print(f"\n🎭 [ASYNC] Autonomous behaviors STARTED for {agent_name}")
        print(f"   Debate ID: {debate_id[:8]}...")
        print(f"   Current Seq: {current_seq}")
        print(f"   Participants: {[p.get('participant_name', 'Unknown') for p in participants]}")
        
        try:
            from .websocket_service import websocket_manager
            from .agent_strategic_actions import AgentStrategicPlanner
            from .database import get_db_connection, get_cursor
            autonomy_service = AgentAutonomyService(self.openrouter_client.api_key)
            strategic_planner = AgentStrategicPlanner(self.openrouter_client.api_key)
            
            # Strategic actions (interrupts, votes, proposals) - 40% chance
            if random.random() < 0.4:
                print(f"   🎯 Checking for strategic actions by {agent_name}...")
                
                policy_config = {}
                with get_db_connection() as conn:
                    cursor = get_cursor(conn)
                    cursor.execute("SELECT policy_config, description FROM debates WHERE debate_id = %s", (debate_id,))
                    row = cursor.fetchone()
                    if row:
                        policy_config = row['policy_config'] or {}
                        problem = row['description'] or "the topic"
                
                current_round = (policy_config.get('total_turns_taken', 0) // len(participants)) + 1
                max_rounds = policy_config.get('max_rounds', 4)
                
                # Build conversation summary
                conversation_summary = "\n".join([
                    f"{h.get('content', {}).get('agent_name', 'Agent')}: {h.get('content', {}).get('text', '')[:200]}"
                    for h in history_events[-5:]
                    if h.get('event_type') == 'agent_message'
                ])
                
                tactical_move = strategic_planner.decide_strategic_action(
                    agent_name, conversation_summary, current_round, max_rounds
                )
                
                if tactical_move:
                    content = {
                        'agent': agent_name,
                        'move': tactical_move,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    event_id = self._persist_autonomous_event(debate_id, 'strategic_action', content)
                    
                    if event_id:
                        event = {
                            'type': 'strategic_action',
                            'debate_id': debate_id,
                            'event_id': event_id,
                            'sender_type': 'system',
                            'payload': content
                        }
                        await websocket_manager.broadcast_to_debate(debate_id, event)
                        print(f"    🎯✅ Strategic action sent: {tactical_move.get('move')} by {agent_name}")
            
            # Coalition formation (60% chance - more aggressive)
            if random.random() < 0.6:
                print(f"   🤝 Checking for coalition formation by {agent_name}...")
                coalition = autonomy_service.analyze_and_form_coalitions(
                    debate_id, agent_name, participants, history_events, desired_outcomes
                )
                
                if coalition:
                    content = {
                        'members': coalition['members'],
                        'strategy': coalition.get('strategy'),
                        'goal': coalition.get('goal', 'Strategic coordination'),
                        'type': coalition.get('type', 'alliance'),
                        'formed_by': agent_name,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # PERSIST TO DATABASE
                    event_id = self._persist_autonomous_event(debate_id, 'coalition_formed', content)
                    
                    if event_id:
                        # Broadcast via WebSocket
                        event = {
                            'type': 'coalition_formed',
                            'debate_id': debate_id,
                            'event_id': event_id,
                            'sender_type': 'system',
                            'payload': content
                        }
                        await websocket_manager.broadcast_to_debate(debate_id, event)
            
            # Question to Host/Moderator (25% chance - occasional questions)
            if random.random() < 0.25:
                # Generate a short clarifying question for the host
                question_prompt = f"""You are {agent_name} in a debate about: {chr(10).join(desired_outcomes[:2]) if desired_outcomes else 'the current topic'}.

Generate a SHORT (max 15 words) clarifying question to ask the moderator/host. Be specific and concise.

Examples:
- "Could you clarify the timeline for implementation?"
- "What's the priority: cost or speed?"
- "Are we considering international markets?"
- "Should we focus on short-term or long-term impact?"

Your question (15 words max):"""
                
                try:
                    response = autonomy_service.openrouter_client.chat_completion(
                        model='openai/gpt-4o-mini',  # Fast and reliable
                        messages=[
                            {"role": "system", "content": "You generate short, specific clarifying questions for debates."},
                            {"role": "user", "content": question_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=50
                    )
                    
                    question = response.get('content', '').strip()
                    if question and len(question.split()) <= 20:  # Enforce brevity
                        content = {
                            'from_agent': agent_name,
                            'to_agent': 'Host',
                            'message': question,
                            'is_question_to_host': True,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        
                        event_id = self._persist_autonomous_event(debate_id, 'private_message', content)
                        
                        if event_id:
                            event = {
                                'type': 'private_message',
                                'debate_id': debate_id,
                                'event_id': event_id,
                                'sender_type': 'system',
                                'payload': content
                            }
                            await websocket_manager.broadcast_to_debate(debate_id, event)
                            print(f"    ❓ Question to Host: {agent_name} → Host: {question[:60]}...")
                except Exception as e:
                    print(f"    ⚠️ Failed to generate host question: {e}")
            
            # Private messaging (CRITICAL - agents must talk!)
            print(f"\n   🔊 PRIVATE MESSAGING CHECK for {agent_name}:")
            print(f"      Participants count: {len(participants)}")
            
            # 80% chance for private messaging (very aggressive)
            if len(participants) >= 2 and random.random() < 0.8:
                print(f"   📨 ✅ 2+ participants, attempting private messaging...")
                other_agents = [
                    (p.get('agent_config') or {}).get('name') or p.get('role_name')
                    for p in participants
                    if ((p.get('agent_config') or {}).get('name') or p.get('role_name')) != agent_name
                ]
                
                print(f"      Other agents available: {other_agents}")
                
                if other_agents:
                    # Check for previous DM from target to current agent (unreplied)
                    from .database import get_db_connection, get_cursor
                    previous_dm = None
                    
                    with get_db_connection() as conn:
                        cursor = get_cursor(conn)
                        try:
                            # Find ALL unreplied DMs sent TO this agent
                            cursor.execute("""
                                SELECT DISTINCT content->>'from_agent' as sender, content->>'message' as message
                                FROM events
                                WHERE debate_id = %s 
                                  AND event_type = 'private_message'
                                  AND content->>'to_agent' = %s
                                  AND content->>'from_agent' != %s
                                  AND NOT EXISTS (
                                    SELECT 1 FROM events e2
                                    WHERE e2.debate_id = %s
                                      AND e2.event_type = 'private_message'
                                      AND e2.content->>'from_agent' = %s
                                      AND e2.content->>'to_agent' = content->>'from_agent'
                                      AND e2.sequence_number > events.sequence_number
                                  )
                                ORDER BY events.sequence_number DESC
                                LIMIT 1
                            """, (debate_id, agent_name, agent_name, debate_id, agent_name))
                            
                            result = cursor.fetchone()
                            if result:
                                # We have an unreplied DM! Reply to it
                                target = result['sender']
                                previous_dm = result['message']
                                print(f"    🔔 Found unreplied DM from {target} to {agent_name}")
                            else:
                                # No unreplied DMs, pick a random target for new conversation
                                target = random.choice(other_agents)
                                print(f"    ✉️  No unreplied DMs, starting new conversation with {target}")
                        finally:
                            cursor.close()
                    
                    # Build context from recent messages
                    context = "\n".join([
                        f"{e.get('content', {}).get('agent_name')}: {e.get('content', {}).get('text', '')[:100]}"
                        for e in history_events[-3:] if e.get('event_type') == 'agent_message'
                    ])
                    
                    # Generate message (reply if previous_dm exists, otherwise initial)
                    print(f"      🤖 Calling LLM to generate DM from {agent_name} to {target}...")
                    print(f"         Model: openai/gpt-oss-20b:free")
                    print(f"         Is Reply: {bool(previous_dm)}")
                    
                    try:
                        message = autonomy_service.generate_private_message(
                            debate_id, agent_name, target, context, desired_outcomes, previous_dm
                        )
                        print(f"      ✅ LLM returned message: {message[:80] if message else 'None'}...")
                    except Exception as e:
                        print(f"      ❌ LLM call FAILED: {e}")
                        message = None
                    
                    if message:
                        content = {
                            'from_agent': agent_name,
                            'to_agent': target,
                            'message': message,
                            'is_reply': bool(previous_dm),
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        
                        # PERSIST TO DATABASE
                        event_id = self._persist_autonomous_event(debate_id, 'private_message', content)
                        
                        if event_id:
                            # Broadcast via WebSocket
                            event = {
                                'type': 'private_message',
                                'debate_id': debate_id,
                                'event_id': event_id,
                                'sender_type': 'system',
                                'payload': content
                            }
                            await websocket_manager.broadcast_to_debate(debate_id, event)
                            print(f"    ✅✅✅ DM SUCCESSFULLY SENT: {agent_name} → {target} {'(REPLY)' if previous_dm else '(NEW)'}")
                            print(f"           Message: {message}")
                    else:
                        print(f"      ❌ Message generation returned None/empty - FAILED")
            else:
                print(f"   ❌ Not enough participants for DMs (need 2+, have {len(participants)})")
            
            print(f"✅ [ASYNC] Autonomous behaviors COMPLETED for {agent_name}\n")
            
        except Exception as e:
            print(f"❌ [ASYNC] Autonomous behaviors ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def _write_to_document_sections(
        self,
        debate_id: str,
        agent_id: str,
        agent_name: str,
        agent_message: str,
        model_id: str,
        system_prompt: str
    ):
        """
        Write agent content to assigned document sections
        """
        print(f"\n📝 DOCUMENT WRITE TRIGGERED:")
        print(f"   Agent: {agent_name}")
        print(f"   Agent ID: {agent_id}")
        print(f"   Debate: {debate_id}")
        print(f"   Message length: {len(agent_message)} chars\n")
        
        try:
            with get_db_connection() as conn:
                cursor = get_cursor(conn)
                
                # Check if there's a document for this debate
                cursor.execute("""
                    SELECT document_id, title, template_id
                    FROM documents
                    WHERE debate_id = %s AND status IN ('draft', 'in_progress')
                    LIMIT 1
                """, (debate_id,))
                
                document = cursor.fetchone()
                if not document:
                    print(f"📄 No active document found for debate {debate_id}")
                    return
                
                document_id = document['document_id']
                
                # Find sections assigned to this agent
                cursor.execute("""
                    SELECT section_id, section_key, section_title, section_type,
                           word_limit, word_count, status, content_schema
                    FROM document_sections
                    WHERE document_id = %s
                      AND assigned_agent_id = %s
                      AND status IN ('assigned', 'pending', 'in_progress')
                    ORDER BY section_order ASC
                """, (document_id, agent_id))
                
                sections = cursor.fetchall()
                if not sections:
                    print(f"📄 No sections assigned to {agent_name} in document {document_id}")
                    return
                
                print(f"\n📄 DOCUMENT WRITING: {agent_name} has {len(sections)} assigned section(s)")
                
                # Write to each assigned section
                for section in sections:
                    section_id = section['section_id']
                    section_title = section['section_title']
                    section_type = section['section_type']
                    word_limit = section['word_limit']
                    current_status = section['status']
                    
                    print(f"   Writing to: {section_title} (type: {section_type}, limit: {word_limit} words)")
                    
                    # Generate section-specific content
                    content = self._generate_section_content(
                        section_title=section_title,
                        section_type=section_type,
                        word_limit=word_limit,
                        agent_name=agent_name,
                        agent_message=agent_message,
                        model_id=model_id,
                        system_prompt=system_prompt,
                        debate_context=f"Debate: {document['title']}"
                    )
                    
                    if not content:
                        continue
                    
                    # Count words
                    word_count = len(content.split())
                    
                    # Update section status
                    new_status = 'completed' if word_count >= (word_limit or 100) else 'in_progress'
                    if current_status == 'pending':
                        new_status = 'in_progress'
                    
                    # Update section in database WITH CONTENT
                    cursor.execute("""
                        UPDATE document_sections
                        SET content = %s,
                            status = %s,
                            word_count = %s,
                            started_at = COALESCE(started_at, NOW()),
                            completed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE completed_at END,
                            updated_at = NOW()
                        WHERE section_id = %s
                    """, (content, new_status, word_count, new_status, section_id))
                    
                    print(f"   ✅ Updated section: {word_count} words, status: {new_status}")
                
                # Update document status if all sections are completed
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                    FROM document_sections
                    WHERE document_id = %s
                """, (document_id,))
                
                counts = cursor.fetchone()
                if counts['total'] > 0 and counts['completed'] == counts['total']:
                    cursor.execute("""
                        UPDATE documents
                        SET status = 'completed',
                            completed_at = NOW()
                        WHERE document_id = %s
                    """, (document_id,))
                    print(f"   🎉 Document {document_id} marked as COMPLETED!")
                else:
                    cursor.execute("""
                        UPDATE documents
                        SET status = 'in_progress'
                        WHERE document_id = %s AND status = 'draft'
                    """, (document_id,))
                
                conn.commit()
                print(f"📄 Document sections updated successfully\n")
                
        except Exception as e:
            print(f"⚠️ Document writing error: {e}")
    
    def _generate_section_content(
        self,
        section_title: str,
        section_type: str,
        word_limit: int,
        agent_name: str,
        agent_message: str,
        model_id: str,
        system_prompt: str,
        debate_context: str
    ) -> str:
        """
        Generate content for a specific document section
        """
        try:
            # For diagram sections, generate Mermaid code
            if section_type == 'diagram':
                prompt = f"""Generate a Mermaid.js diagram for the section titled "{section_title}".

Context: {debate_context}

Based on this discussion point: {agent_message[:500]}

Create a clear, professional Mermaid diagram (flowchart, sequence, or ER diagram as appropriate).
Return ONLY the Mermaid code, no explanations."""
                
                messages = [
                    {"role": "system", "content": "You are a technical documentation expert who creates clear Mermaid.js diagrams."},
                    {"role": "user", "content": prompt}
                ]
                
            else:
                # For text sections, summarize the agent's point for this section
                prompt = f"""Write content for the document section titled "{section_title}".

Context: {debate_context}

Your role: {system_prompt[:200] if system_prompt else agent_name}

Based on your contribution to the debate: {agent_message}

Requirements:
- Write {word_limit} words or less
- Focus on the specific aspect covered by "{section_title}"
- Be concise and professional
- Use bullet points or short paragraphs
- Return only the content, no meta-commentary"""
                
                messages = [
                    {"role": "system", "content": f"You are {agent_name}, contributing to a collaborative document."},
                    {"role": "user", "content": prompt}
                ]
            
            # Call LLM to generate content
            response = self.openrouter_client.chat_completion(
                model=model_id,
                messages=messages,
                max_tokens=word_limit * 2 if section_type != 'diagram' else 500,
                temperature=0.7
            )
            
            content = response.get('content', '').strip()
            
            # For diagrams, clean up markdown code blocks if present
            if section_type == 'diagram' and content:
                # Remove markdown code blocks
                content = content.replace('```mermaid', '').replace('```', '').strip()
            
            return content
            
        except Exception as e:
            print(f"⚠️ Section content generation error: {e}")
            return ""
    
    def _generate_with_constitutional_pipeline(
        self,
        debate_id: str,
        agent_name: str,
        agent_config: Dict[str, Any],
        model_id: str,
        conversation_history: List[Dict[str, str]],
        messages: List[Dict[str, str]],
        debate_context: Dict[str, Any],
        turn_info: Dict[str, Any],
        participants: List[Dict[str, Any]],
        history_events: List[Dict[str, Any]]
    ) -> str:
        """
        Generate agent response using 3-stage Constitutional AI pipeline
        
        Stage 1: Reasoning - Agent evaluates stance
        Stage 2: Response - Generate message
        Stage 3: Validation - Constitutional checks
        
        Returns:
            Final validated agent message
        """
        try:
            # Get agent memory
            agent_memory = AgentMemory(debate_id, agent_name)
            past_messages = agent_memory.get_past_messages(limit=3)
            past_messages_text = [msg["text"] for msg in past_messages]
            memory_context = agent_memory.build_memory_context()
            
            # Get user interventions
            user_interventions = agent_memory.get_user_interventions()
            latest_intervention = user_interventions[0]["text"] if user_interventions else None
            
            # Extract recent conversation for reasoning
            recent_conversation = "\n".join([
                f"{msg['role']}: {msg['content'][:300]}..."
                for msg in conversation_history[-5:]
                if msg['role'] in ['user', 'assistant']
            ])
            
            # Get list of ALL valid participant names (for hallucination check)
            # The validator needs ALL names to detect if agent mentions someone who doesn't exist
            all_participant_names = [
                (p['agent_config'] or {}).get('name') or p['role_name']
                for p in participants
            ]
            
            # Get list of participants who have spoken (for prompt context)
            participants_who_spoke = list(set(
                event.get('content', {}).get('agent_name')
                for event in history_events
                if event.get('event_type') == 'agent_message' and event.get('content', {}).get('agent_name')
            ))
            
            # Start thinking session
            turn_num = turn_info.get('turn_number', 0)
            print(f"\n🧠🧠🧠 STARTING THINKING SESSION FOR {agent_name} 🧠🧠🧠")
            session_id = self.thinking_service.start_thinking_session(debate_id, agent_name, turn_num)
            print(f"    Session ID: {session_id}")
            
            # STAGE 1: REASONING
            print(f"  Stage 1: Reasoning...")
            print(f"🧠 About to emit reasoning thinking step...")
            self.thinking_service.emit_thinking_step(debate_id, agent_name, "reasoning", {
                "stage": "Stage 1: Reasoning",
                "status": "Evaluating stance and analyzing recent messages...",
                "details": [
                    f"Reading {len(past_messages)} past messages from this agent",
                    f"Analyzing {len(conversation_history[-5:])} recent conversation turns",
                    f"Checking for user interventions: {'Yes' if latest_intervention else 'None'}",
                    f"Comparing with {len(participants_who_spoke)} agents who have spoken"
                ]
            })
            
            reasoning = self.reasoning_engine.evaluate_stance(
                agent_name=agent_name,
                agent_role=agent_config.get('description', agent_config.get('system_prompt', '')[:100]),
                past_positions=memory_context,
                recent_conversation=recent_conversation,
                user_intervention=latest_intervention
            )
            print(f"    Stance: {reasoning['current_stance'][:60]}...")
            print(f"    Confidence: {reasoning['confidence']}")
            print(f"    Changed: {reasoning['stance_changed']}")
            
            self.thinking_service.emit_thinking_step(debate_id, agent_name, "reasoning_complete", {
                "stage": "Stage 1: Complete",
                "status": "Reasoning complete",
                "details": [
                    f"Stance: {reasoning['current_stance'][:80]}...",
                    f"Confidence: {reasoning['confidence']}",
                    f"Stance changed: {reasoning['stance_changed']}",
                    f"Key points identified: {len(reasoning.get('key_points', []))}"
                ]
            })
            
            # STAGE 2: RESPONSE GENERATION
            print(f"  Stage 2: Generating response...")
            self.thinking_service.emit_thinking_step(debate_id, agent_name, "generating", {
                "stage": "Stage 2: Generating Response",
                "status": "Crafting message based on reasoning...",
                "details": [
                    f"Using stance: {reasoning['current_stance'][:60]}...",
                    f"Incorporating debate rules and personality",
                    f"Checking for direct challenges to respond to",
                    f"Ensuring authentic character voice"
                ]
            })
            
            agent_message = self.response_generator.generate_response(
                agent_name=agent_name,
                agent_role_description=agent_config.get('system_prompt', ''),
                reasoning=reasoning,
                conversation_history=conversation_history,
                debate_context=debate_context,
                turn_info=turn_info
            )
            print(f"    Generated {len(agent_message)} chars")
            
            self.thinking_service.emit_thinking_step(debate_id, agent_name, "generating_complete", {
                "stage": "Stage 2: Complete",
                "status": "Response generated",
                "details": [
                    f"Message length: {len(agent_message)} characters",
                    f"Estimated words: ~{len(agent_message.split())}",
                    f"Contains citations: {'Yes' if '[' in agent_message or '(' in agent_message else 'No'}"
                ]
            })
            
            # STAGE 3: CONSTITUTIONAL VALIDATION
            print(f"  Stage 3: Validating...")
            
            # Get recent messages from OTHER agents (for repetition check)
            recent_other_messages = []
            for event in reversed(history_events[-5:]):
                if event.get('event_type') == 'agent_message':
                    other_agent = event.get('content', {}).get('agent_name')
                    if other_agent and other_agent != agent_name:
                        recent_other_messages.append(event.get('content', {}).get('text', ''))
                        if len(recent_other_messages) >= 3:
                            break
            recent_other_messages.reverse()  # Chronological order
            
            self.thinking_service.emit_thinking_step(debate_id, agent_name, "validating", {
                "stage": "Stage 3: Validation",
                "status": "Checking message against constitutional rules...",
                "details": [
                    "Checking for hallucinations (invalid participant mentions)",
                    "Checking for flip-flopping (consistency with past stance)",
                    "Checking for repetition (echoing other agents)",
                    "Checking for self-contradiction",
                    f"Validating against {len(all_participant_names)} valid participants"
                ]
            })
            
            validation = self.constitutional_validator.validate(
                message=agent_message,
                reasoning=reasoning,
                agent_name=agent_name,
                agent_role=agent_config.get('description', ''),
                past_messages=past_messages_text,
                active_participants=all_participant_names,  # All valid names, not just those who spoke
                recent_other_messages=recent_other_messages
            )
            
            if not validation["valid"]:
                print(f"    ⚠️ Constitutional violations:")
                for violation in validation["violations"]:
                    print(f"      - {violation['rule']}: {violation['details']}")
                
                self.thinking_service.emit_thinking_step(debate_id, agent_name, "validation_issues", {
                    "stage": "Stage 3: Issues Found",
                    "status": "Constitutional violations detected",
                    "details": [f"⚠️ {v['rule']}: {v['details']}" for v in validation["violations"][:3]]
                })
                
                # Use corrected message if available
                if validation["corrected_message"]:
                    print(f"    ✅ Auto-corrected")
                    agent_message = validation["corrected_message"]
                    self.thinking_service.emit_thinking_step(debate_id, agent_name, "auto_corrected", {
                        "stage": "Stage 3: Auto-Corrected",
                        "status": "Message automatically fixed",
                        "details": ["Applied automatic corrections", "Message ready to send"]
                    })
                elif validation["needs_regeneration"]:
                    print(f"    🔄 Needs regeneration - using constrained retry")
                    self.thinking_service.emit_thinking_step(debate_id, agent_name, "regenerating", {
                        "stage": "Stage 3: Regenerating",
                        "status": "Creating new message with stricter constraints...",
                        "details": ["Previous message violated rules", "Regenerating with specific fixes"]
                    })
                    
                    # Build specific constraint based on violation type
                    violation_rules = [v['rule'] for v in validation['violations']]
                    constraints = [
                        f"Your previous message violated: {', '.join(violation_rules)}",
                        "",
                        "You MUST:"
                    ]
                    
                    if 'no_repetition' in violation_rules:
                        constraints.extend([
                            "- DO NOT repeat what others just said",
                            "- Add NEW data, evidence, or reasoning that others haven't mentioned",
                            "- OR disagree and explain WHY they're wrong",
                            f"- Others said: {reasoning.get('what_others_said', 'see above')}"
                        ])
                    
                    if 'no_flip_flop' in violation_rules:
                        constraints.append("- Maintain your previous position unless you explicitly justify changes")
                    
                    if 'no_hallucination' in violation_rules:
                        constraints.append(f"- Only reference participants from this list: {', '.join(active_participants)}")
                    
                    constraints.extend([
                        f"- Follow your role as {agent_config.get('description', 'agent')}",
                        "",
                        "Regenerate your response following these rules."
                    ])
                    
                    # Fallback: Use legacy approach with strong constraints
                    response = self.openrouter_client.chat_completion(
                        model=model_id,
                        messages=messages + [{
                            "role": "system",
                            "content": "\n".join(constraints)
                        }],
                        temperature=0.7,  # Lower temp for constrained regeneration
                        max_tokens=900
                    )
                    agent_message = response['content']
            else:
                print(f"    ✅ Validation passed")
                self.thinking_service.emit_thinking_step(debate_id, agent_name, "validation_complete", {
                    "stage": "Stage 3: Complete",
                    "status": "✅ All checks passed",
                    "details": [
                        "No hallucinations detected",
                        "Consistent with past stance",
                        "Not repeating others",
                        "Message approved"
                    ]
                })
            
            # Complete thinking session and persist summary
            self.thinking_service.complete_thinking_session()
            
            return agent_message
            
        except Exception as e:
            print(f"  ⚠️ Constitutional pipeline error: {e}")
            print(f"  📞 Falling back to legacy approach")
            # Fallback to legacy single LLM call
            response = self.openrouter_client.chat_completion(
                model=model_id,
                messages=messages,
                temperature=0.9,
                max_tokens=900
            )
            return response['content']
