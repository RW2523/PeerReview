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
            system_prompt = agent_config.get('system_prompt', '')
            
            # Debug: Print agent name extraction
            print(f"🔍 AGENT NAME DEBUG:")
            print(f"   Participant ID: {next_participant['participant_id']}")
            print(f"   Role name from DB: {next_participant['role_name']}")
            print(f"   Agent config keys: {list(agent_config.keys())}")
            print(f"   Agent config 'name': {agent_config.get('name')}")
            print(f"   FINAL agent_name variable: {agent_name}\n")
            
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
            recent_human_messages = []
            for event in reversed(history_events[-5:]):  # Check last 5 events
                if event['event_type'] == 'human_message':
                    content = event.get('content') or {}
                    text = content.get('text', '')
                    actor = content.get('actor', 'Moderator')
                    recent_human_messages.append(f"{actor}: {text}")
            
            if recent_human_messages:
                # Add as a HIGH PRIORITY system message that demands response
                messages.append({
                    "role": "system",
                    "content": f"""🚨 URGENT MODERATOR INTERVENTION 🚨

The moderator has directly addressed the debate participants. You MUST acknowledge and respond to this intervention:

{chr(10).join(f"• {msg}" for msg in recent_human_messages)}

⚠️ CRITICAL: Your next response MUST explicitly address this moderator message. Start your response by acknowledging what the moderator said."""
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
                    participants_spoken.append(f"@{name}")
            
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
2. CITATION RULE: Only reference and cite agents who are listed as "Active" (with @). DO NOT mention, cite, or reference any participant who hasn't spoken yet. 
3. Base your response ONLY on:
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
                    'turn': total_turns + 1,
                    'turn_index': current_turn_index
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
            
            # Post-turn autonomous behaviors (50% chance, more visible)
            should_trigger_autonomy = random.random() < 0.50 and total_turns > 1
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
                # Make human interventions prominent in history
                history.append({
                    "role": "user",
                    "content": f"🎙️ **MODERATOR INTERVENTION by {actor}**:\n\n{text}\n\n[This is a direct moderator message that requires acknowledgment]"
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
                    SELECT COALESCE(MAX(sequence_number), 0) + 1
                    FROM events
                    WHERE debate_id = %s
                """, (debate_id,))
                sequence_number = cursor.fetchone()['coalesce']
                
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
            
            # Coalition formation (50% of 25% = 12.5% overall)
            if random.random() < 0.5:
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
            
            # Private messaging with back-and-forth (60% chance - agents love to DM!)
            if random.random() < 0.6 and len(participants) >= 2:
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
