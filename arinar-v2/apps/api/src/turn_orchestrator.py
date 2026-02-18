"""Turn-based debate orchestration for M2+"""
import uuid
import random
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import psycopg2.extras
from .database import get_db_connection, get_cursor
from .openrouter_client import OpenRouterClient
from .agent_autonomy import AgentAutonomyService


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
            
            # Get debate history for context
            cursor.execute("""
                SELECT event_type, sender_type, sender_id, content, sequence_number, created_at
                FROM events
                WHERE debate_id = %s
                ORDER BY sequence_number ASC
                LIMIT 50
            """, (debate_id,))
            
            history_events = cursor.fetchall()
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
            
            # Build list of participants who have already spoken (for @mentions)
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
                participant_list = f"Active: {', '.join(participants_spoken)}"
                if unspoken_count > 0:
                    participant_list += f" | {unspoken_count} other participant(s) haven't spoken yet"
            else:
                participant_list = f"You're speaking first! {total_other_participants} other participant(s) will respond after you."
            
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
                    length_instruction = f"This is the first of {max_rounds} rounds. Focus on EXPLORING the topic, ASKING QUESTIONS, and sharing initial observations. Don't rush to conclusions - you have {max_rounds - 1} more rounds to develop your stance. Listen and engage with others."
                else:
                    urgency = f"Round {current_round}/{max_rounds}"
                    length_instruction = f"You're in round {current_round} of {max_rounds}. Build on what others said in previous rounds. Challenge or support their points. Keep it short (4-5 sentences). Save your final decision for round {max_rounds}."
            else:
                urgency = f"Turn {total_turns + 1}"
                length_instruction = "Keep it short and crisp (4-5 sentences). Only expand if making a critical point."
            
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

⚠️ CRITICAL RULES:
1. TEMPORAL AWARENESS: Today is {current_date_str}. When discussing events, policies, or data, always consider recency and note if information is outdated.
2. CITATION RULE: Only reference and cite agents who are listed as "Active" (with @). DO NOT mention, cite, or reference any participant who hasn't spoken yet. ALWAYS use the FULL NAME exactly as shown in the Active list (e.g., '@"Senior Designer (Research-led)"' not just '@Senior'). 
3. COMPREHENSIVE COVERAGE RULE: If the problem statement or moderator question has MULTIPLE parts (e.g., "analyze both Democrats AND Republicans", "address three factors"), you MUST cover ALL parts equally and thoroughly. DO NOT focus disproportionately on one aspect while ignoring others. 
4. MULTI-PART QUESTION RULE: When moderator asks a question with multiple parts (e.g., "why X, Y, and Z?"), you MUST explicitly address EVERY SINGLE part in your response. Number your answers if helpful (1. X because... 2. Y because... 3. Z because...).
5. Base your response ONLY on:
   - Your own preparation notes
   - What Active participants have actually said
   - The debate topic and materials
   - Current temporal context

**Your Response:**
{length_instruction}

**Communication Style - BE CONVERSATIONAL AND ORGANIC:**
- **BUILD ON others**: If an Active participant said "time is of essence", don't repeat that phrase. Instead say "@TheirName makes a great point about urgency..." or "I agree we need to act quickly, and I'd add..."
- **NO ROBOTIC REPETITION**: Avoid copying exact phrases. Each agent should have their own voice and phrasing.
- **USE @mentions for ACTIVE participants ONLY**: Directly address who you're responding to (e.g., "@ActiveAgent, your point about...")
- **REACT genuinely**: Agree/disagree with SPECIFIC points from Active participants, not generic statements
- **ASK FOLLOW-UP questions**: "What do you think about X?" or "How would you address Y?"
- **VARY your language**: If someone says "crucial", you might say "vital" or "essential" - don't parrot the same words
- **BE OPEN-MINDED**: Don't come with pre-determined conclusions unless it's your final turn
- **CRITICAL**: NEVER reference or address participants who are not listed as "Active" above

**Desired Outcomes to Keep in Mind:**
{chr(10).join(f'- {outcome}' for outcome in desired_outcomes) if desired_outcomes else 'No specific outcomes defined'}"""
            
            messages.append({
                "role": "user",
                "content": conversational_instruction
            })
            
            # Call OpenRouter
            response = self.openrouter_client.chat_completion(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            agent_message = response['content']
            
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
            
            # 📄 Document Integration: Write to assigned sections
            self._write_to_document_sections(
                debate_id=debate_id,
                agent_id=next_participant['participant_id'],
                agent_name=agent_name,
                agent_message=agent_message,
                model_id=model_id,
                system_prompt=system_prompt
            )
            
            result = {
                'event_id': event_id,
                'participant_id': next_participant['participant_id'],
                'participant_name': agent_name,
                'message': agent_message,
                'turn_number': total_turns + 1,
                'sequence_number': next_seq
            }
            
            # Post-turn autonomous behaviors (80% chance for better visibility, more visible)
            should_trigger_autonomy = random.random() < 0.80 and total_turns > 1
            if should_trigger_autonomy:
                print(f"    🎭 Triggering autonomous behaviors for {agent_name}...")
                try:
                    # Fire and forget - don't block the turn response
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        asyncio.create_task(
                            self._async_autonomous_behaviors(
                                debate_id, agent_name, participants, history_events, 
                                desired_outcomes, next_seq
                            )
                        )
                except Exception as e:
                    print(f"    ⚠️ Failed to start autonomous behaviors: {e}")
            
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
        
        # Limit history to last 10 messages to avoid context overflow
        return history
    
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
        try:
            from .websocket_service import websocket_manager
            autonomy_service = AgentAutonomyService(self.openrouter_client.api_key)
            
            # Coalition formation (70% chance when autonomy triggers)
            if random.random() < 0.70:
                coalition = autonomy_service.analyze_and_form_coalitions(
                    debate_id, agent_name, participants, history_events, desired_outcomes
                )
                
                if coalition:
                    content = {
                        'members': coalition['members'],
                        'strategy': coalition.get('strategy'),
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
            
            # Question to Host/Moderator (30% chance - agents can ask for clarification)
            if random.random() < 0.30:
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
                        model='google/gemini-flash-1.5',  # Most cost-effective: $0.075/$0.30 (4x cheaper!)
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
            
            # Private messaging with back-and-forth (90% chance - agents love to DM!)
            if random.random() < 0.90 and len(participants) >= 2:
                other_agents = [
                    (p.get('agent_config') or {}).get('name') or p.get('role_name')
                    for p in participants
                    if ((p.get('agent_config') or {}).get('name') or p.get('role_name')) != agent_name
                ]
                
                if other_agents:
                    target = random.choice(other_agents)
                    context = "\n".join([
                        f"{e.get('content', {}).get('agent_name')}: {e.get('content', {}).get('text', '')[:80]}"
                        for e in history_events[-3:] if e.get('event_type') == 'agent_message'
                    ])
                    
                    # Check for previous DM from target to current agent (unreplied)
                    from .database import get_db_connection, get_cursor
                    previous_dm = None
                    
                    with get_db_connection() as conn:
                        cursor = get_cursor(conn)
                        try:
                            cursor.execute("""
                                SELECT content FROM events
                                WHERE debate_id = %s AND event_type = 'private_message'
                                  AND content->>'from_agent' = %s
                                  AND content->>'to_agent' = %s
                                ORDER BY sequence_number DESC LIMIT 1
                            """, (debate_id, target, agent_name))
                            
                            result = cursor.fetchone()
                            if result:
                                # Check if current agent already replied
                                cursor.execute("""
                                    SELECT COUNT(*) as count FROM events
                                    WHERE debate_id = %s AND event_type = 'private_message'
                                      AND content->>'from_agent' = %s
                                      AND content->>'to_agent' = %s
                                      AND sequence_number > (
                                        SELECT sequence_number FROM events
                                        WHERE debate_id = %s AND event_type = 'private_message'
                                          AND content->>'from_agent' = %s
                                          AND content->>'to_agent' = %s
                                        ORDER BY sequence_number DESC LIMIT 1
                                      )
                                """, (debate_id, agent_name, target, debate_id, target, agent_name))
                                
                                if cursor.fetchone()['count'] == 0:
                                    previous_dm = result['content'].get('message')
                        finally:
                            cursor.close()
                    
                    # Generate message (reply if previous_dm exists, otherwise initial)
                    message = autonomy_service.generate_private_message(
                        debate_id, agent_name, target, context, desired_outcomes, previous_dm
                    )
                    
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
        except Exception as e:
            print(f"⚠️ Autonomous behaviors error: {e}")
    
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
                    
                    # Update section in database
                    cursor.execute("""
                        UPDATE document_sections
                        SET status = %s,
                            word_count = %s,
                            started_at = COALESCE(started_at, NOW()),
                            completed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE completed_at END
                        WHERE section_id = %s
                    """, (new_status, word_count, new_status, section_id))
                    
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
