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
        Agent analyzes the conversation and decides if they should form a coalition.
        
        Returns coalition details if one should be formed, None otherwise.
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
        
        coalition_prompt = f"""You are {current_agent_name}. Analyze if you should form a coalition with other participants.

**Desired Outcomes**: {', '.join(desired_outcomes) if desired_outcomes else 'N/A'}

**Other Participants and Their Positions**:
{chr(10).join(participant_summaries)}

**Question**: Should you form a coalition? If yes, with whom?

**Rules**:
- Only form coalitions if there's clear alignment on key points
- Be strategic - coalitions should advance the desired outcomes
- You can ally with 1-2 others maximum

**Respond in JSON format**:
{{"should_form_coalition": true/false, "members": ["Agent1", "Agent2"], "strategy": "Brief 1-sentence reason"}}

If you should NOT form a coalition, respond: {{"should_form_coalition": false}}

Be token-efficient: Keep strategy to max 15 words."""
        
        try:
            response = self.openrouter_client.chat_completion(
                model='openai/gpt-4o-mini',  # Use cheap model for autonomy
                messages=[
                    {"role": "system", "content": "You are an autonomous strategic agent. Respond ONLY with valid JSON, no other text."},
                    {"role": "user", "content": coalition_prompt}
                ],
                temperature=0.3,  # Lower temp for structured output
                max_tokens=100  # Keep it brief
            )
            
            import json
            decision = json.loads(response['content'])
            
            if decision.get('should_form_coalition'):
                coalition = {
                    'members': [current_agent_name] + decision.get('members', []),
                    'strategy': decision.get('strategy', 'Strategic alliance')
                }
                print(f"    ✅ Coalition decision: {coalition}")
                return coalition
            else:
                print(f"    ℹ️  {current_agent_name} chose not to form coalition")
        except Exception as e:
            print(f"    ⚠️ Coalition analysis failed: {e}")
        
        return None
    
    def generate_private_message(
        self,
        debate_id: str,
        from_agent: str,
        to_agent: str,
        conversation_context: str,
        desired_outcomes: List[str]
    ) -> Optional[str]:
        """
        Generate a private message from one agent to another.
        Token-efficient: max 50 words.
        """
        
        message_prompt = f"""You are {from_agent}. Send a brief private message to {to_agent}.

**Context**: {conversation_context[:300]}
**Desired Outcomes**: {', '.join(desired_outcomes) if desired_outcomes else 'N/A'}

**Your Task**: Write a strategic private message (max 30 words) to {to_agent}. 
This is private - other participants won't see it.

Suggest an alliance, share a concern, or propose a joint strategy.

Respond with ONLY the message text, nothing else."""
        
        try:
            response = self.openrouter_client.chat_completion(
                model='openai/gpt-4o-mini',
                messages=[{"role": "user", "content": message_prompt}],
                temperature=0.5,
                max_tokens=60
            )
            
            message = response['content'][:200]  # Cap at 200 chars
            print(f"    ✅ Private message: {from_agent} → {to_agent}: {message[:50]}...")
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
