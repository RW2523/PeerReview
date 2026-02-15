"""
Agent Autonomy Service
Handles autonomous agent behaviors: coalition formation, private messaging, sub-task planning
"""

import uuid
import psycopg2.extras
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .database import get_db_connection, get_cursor
from .openrouter_client import OpenRouterClient


class AgentAutonomyService:
    """
    Manages autonomous agent behaviors between turns:
    - Coalition formation (agents decide who to ally with)
    - Private messaging (agents negotiate strategies)
    - Sub-task planning (agents break down goals)
    """
    
    def __init__(self, openrouter_api_key: str):
        self.openrouter_client = OpenRouterClient(openrouter_api_key)
    
    def analyze_and_form_coalitions(
        self, 
        debate_id: str, 
        current_agent_name: str,
        all_participants: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        desired_outcomes: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Agent decides if they vibe with someone - could be alliance, rivalry, or just respect.
        
        Returns coalition details if they feel strongly about someone, None otherwise.
        """
        
        # Build context for coalition decision
        other_participants = [
            p for p in all_participants 
            if (p.get('agent_config') or {}).get('name') != current_agent_name
        ]
        
        if len(other_participants) < 1:
            return None  # Need at least one other agent
        
        participant_summaries = []
        for p in other_participants:
            name = (p.get('agent_config') or {}).get('name') or p.get('role_name', 'Agent')
            # Find their recent messages
            messages = [
                h['content'].get('text', '')[:150] 
                for h in conversation_history 
                if h.get('content', {}).get('agent_name') == name
            ]
            recent = messages[-1] if messages else "Has not spoken yet"
            participant_summaries.append(f"- {name}: {recent}")
        
        coalition_prompt = f"""You are {current_agent_name}. React HUMANLY to what others said. You can form alliances OR rivalries.

**Other Participants:**
{chr(10).join(participant_summaries)}

**Your Options:**
1. **Alliance**: You genuinely agree with someone's points → Form supportive coalition
2. **Rivalry**: You think someone's logic is weak → Form opposition coalition  
3. **Nothing**: No strong feelings this turn

**Examples:**
- Alliance: {{"should_form_coalition": true, "members": ["You", "Agent1"], "strategy": "We're both data-driven", "type": "alliance"}}
- Rivalry: {{"should_form_coalition": true, "members": ["You", "Agent2"], "strategy": "Their logic is flawed", "type": "rivalry"}}
- Nothing: {{"should_form_coalition": false}}

**Rules:**
- BE HONEST: If someone said something dumb, you can oppose them
- BE SUPPORTIVE: If someone made a great point, ally with them
- BE SELECTIVE: Don't force it - only if you feel strongly
- Max 2 people per coalition

**Respond in JSON (max 12 words for strategy):**"""
        
        try:
            response = self.openrouter_client.chat_completion(
                model='openai/gpt-4o-mini',  # Use cheap model for autonomy
                messages=[
                    {"role": "system", "content": "You are a human-like agent with opinions. Respond ONLY with valid JSON, no other text."},
                    {"role": "user", "content": coalition_prompt}
                ],
                temperature=0.7,  # Higher temp for more personality
                max_tokens=100  # Keep it brief
            )
            
            import json
            decision = json.loads(response['content'])
            
            if decision.get('should_form_coalition'):
                coalition_type = decision.get('type', 'alliance')
                coalition = {
                    'members': [current_agent_name] + decision.get('members', []),
                    'strategy': decision.get('strategy', 'Strategic alliance'),
                    'type': coalition_type
                }
                emoji = '🤝' if coalition_type == 'alliance' else '⚔️'
                print(f"    {emoji} {coalition_type.upper()} formed by {current_agent_name}: {coalition}")
                return coalition
            else:
                print(f"    ℹ️  {current_agent_name} chose NOT to form coalition this turn")
        except Exception as e:
            print(f"    ⚠️ Coalition analysis failed: {e}")
        
        return None
    
    def generate_private_message(
        self,
        debate_id: str,
        from_agent: str,
        to_agent: str,
        conversation_context: str,
        desired_outcomes: List[str],
        previous_dm: Optional[str] = None
    ) -> Optional[str]:
        """Generate human-like private message with personality"""
        
        # Add previous DM context if this is a reply
        previous_context = ""
        if previous_dm:
            previous_context = f"\n**Previous message from {to_agent}:**\n{previous_dm}\n\n(You're REPLYING to this message)\n"
        
        message_prompt = f"""You are {from_agent}. Send a HUMAN-LIKE private DM to {to_agent}.
{previous_context}
**Recent conversation:**
{conversation_context[:300]}

**Your Options (pick ONE tone):**
1. Supportive: "Great point about X! I'm with you on that."
2. Critical: "That reasoning was weak - you missed Y entirely."
3. Sarcastic: "Oh wow, brilliant logic there"
4. Strategic: "Let's team up on Z - they're not seeing it."
5. Trolling: "Did you really just say that? Come on"
6. Friendly: "Yo, I like your thinking here!"
7. Confrontational: "You're dead wrong about X"

**Rules:**
- BE HONEST AND HUMAN: React genuinely to what they said
- MAX 25 WORDS: Keep it punchy
- NO CORPORATE SPEAK: Talk like a real person
- This is PRIVATE - other agents cannot see it

**Respond with ONLY the message text:**"""
        
        try:
            response = self.openrouter_client.chat_completion(
                model='openai/gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "You are a human with personality. Be genuine, witty, or critical as needed."},
                    {"role": "user", "content": message_prompt}
                ],
                temperature=0.8,  # High temp for more personality
                max_tokens=60
            )
            
            message = response['content'].strip().strip('"\'')[:200]  # Cap at 200 chars, remove quotes
            print(f"    💬 Private message: {from_agent} → {to_agent}: {message[:60]}...")
            return message
        except Exception as e:
            print(f"    ⚠️ Private message generation failed: {e}")
            return None
    
    def plan_subtasks(
        self,
        debate_id: str,
        agent_name: str,
        problem_statement: str,
        desired_outcomes: List[str]
    ) -> List[str]:
        """
        Agent breaks down the problem into sub-tasks.
        Token-efficient: max 3 sub-tasks, each under 15 words.
        """
        
        subtask_prompt = f"""You are {agent_name}. Break down this problem into 2-3 actionable sub-tasks.

**Problem**: {problem_statement[:200]}
**Desired Outcomes**: {', '.join(desired_outcomes[:2]) if desired_outcomes else 'N/A'}

**List 2-3 sub-tasks (each max 12 words). Format:**
1. [Task 1]
2. [Task 2]
3. [Task 3]

Be specific and actionable. Keep it brief."""
        
        try:
            response = self.openrouter_client.chat_completion(
                model='openai/gpt-4o-mini',
                messages=[{"role": "user", "content": subtask_prompt}],
                temperature=0.4,
                max_tokens=80
            )
            
            # Parse numbered list
            tasks = []
            for line in response['content'].split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    task = line.lstrip('0123456789.-) ').strip()
                    if task:
                        tasks.append(task[:100])  # Cap each task
            
            return tasks[:3]  # Max 3 tasks
        except Exception as e:
            print(f"    ⚠️ Sub-task planning failed: {e}")
            return []
