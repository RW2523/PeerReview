"""
Agent Response Generator - Stage 2 of Constitutional AI Pipeline

Anthropic-inspired: Generate the actual debate message based on
the reasoning from Stage 1.

This separates "what to say" from "how to say it".
"""
from typing import Dict, Any, List, Optional
from .openrouter_client import OpenRouterClient


class AgentResponseGenerator:
    """
    Stage 2: Generates debate message based on reasoning output
    
    Input: Structured reasoning from Stage 1
    Output: Natural debate message
    """
    
    def __init__(self, openrouter_api_key: str):
        self.client = OpenRouterClient(openrouter_api_key)
    
    def generate_response(
        self,
        agent_name: str,
        agent_role_description: str,
        reasoning: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        debate_context: Dict[str, Any],
        turn_info: Dict[str, Any],
        debate_id: Optional[str] = None,
    ) -> str:
        """
        Generate debate message based on reasoning
        
        Args:
            agent_name: Agent's name
            agent_role_description: Full role/persona description
            reasoning: Output from Stage 1 (reasoning engine)
            conversation_history: Recent messages
            debate_context: Topic, agenda, outcomes
            turn_info: Round number, urgency, etc.
        
        Returns:
            Natural debate message (150-300 words)
        """
        
        # Build system prompt with reasoning constraints
        system_prompt = self._build_system_prompt(
            agent_name,
            agent_role_description,
            reasoning,
            turn_info
        )
        
        # Build conversation context
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": self._format_debate_context(debate_context)}
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add reasoning as instruction
        messages.append({
            "role": "system",
            "content": f"""Your reasoning (from Stage 1):
- Current stance: {reasoning['current_stance']}
- Confidence: {reasoning['confidence']}
- Stance changed: {reasoning['stance_changed']}
- Key points to make: {', '.join(reasoning['key_points'])}

Now generate your debate message following this reasoning."""
        })
        
        try:
            response = self.client.chat_completion(
                model="openai/gpt-4o-mini",
                messages=messages,
                temperature=0.85,
                max_tokens=900,
                _debate_id=debate_id,
                _stage="response_generation",
                _participant=agent_name,
            )
            
            return response["content"].strip()
            
        except Exception as e:
            print(f"⚠️ Response generation error: {e}")
            # Fallback to basic response
            return f"[{agent_name}] {reasoning['current_stance']} {'. '.join(reasoning['key_points'])}"
    
    def _build_system_prompt(
        self,
        agent_name: str,
        role_description: str,
        reasoning: Dict[str, Any],
        turn_info: Dict[str, Any]
    ) -> str:
        """Build system prompt with constitutional constraints"""
        
        # Build stance change instruction
        stance_instruction = ""
        if reasoning.get("stance_changed"):
            stance_instruction = f"""
⚠️ YOU ARE CHANGING YOUR STANCE THIS TURN.
You MUST start your message with:
"I'm revising my position because {reasoning.get('reason_for_change', 'new information has emerged')}..."

Then explain your new stance.
"""
        else:
            stance_instruction = """
✅ MAINTAIN YOUR CURRENT STANCE.
Build on your previous arguments. Reference what you said before.
If others disagree, defend your position with new angles.
"""
        
        # Build disagreement instruction
        disagree_instruction = ""
        if reasoning.get("should_disagree_with"):
            targets = ", ".join(f"@\"{name}\"" for name in reasoning["should_disagree_with"])
            disagree_instruction = f"""
💥 CRITICAL: Challenge {targets} directly.
Call out flaws in their reasoning. Don't be polite - be sharp and precise.
"""
        
        # Universal debate rules (topic-agnostic)
        universal_rules = """
📋 UNIVERSAL DEBATE RULES:

1. **Intellectual Consistency**: Don't contradict yourself. If your view evolved, explain why.
2. **Address Others Directly**: Use @mentions. Quote specific points. Be conversational.
3. **Add New Information**: Don't repeat what's already said. Advance the discussion.
4. **Be Specific**: Vague claims lose debates. Give examples, data, reasoning.
5. **Question Assumptions**: Challenge premises. Ask "why?" and "what if?".

GOOD EXAMPLES (work for any topic):
✅ "@Visionary raised X, but here's the flaw: [specific counter]. My position remains Y because [new reasoning]."
✅ "I'm changing my view. Originally I thought A, but @Analyst's point about B changes the calculus. New position: C."
✅ "Hold on. Everyone's assuming X, but what if Y? That would completely shift this to [alternative]."

BAD EXAMPLES (never do this):
❌ "I agree with everyone." (No independent thought)
❌ "X is best. Actually Y is best." (Flip-flop without justification)
❌ "That's a good point." (Too vague, no substance)
"""
        
        return f"""{role_description}

{stance_instruction}

{disagree_instruction}

{universal_rules}

TURN CONTEXT: {turn_info.get('urgency', 'Mid-debate')} | Round {turn_info.get('current_round', '?')}/{turn_info.get('max_rounds', '?')}
LENGTH: {turn_info.get('length_instruction', '150-250 words, punchy and direct')}

Generate your debate message now."""
    
    def _format_debate_context(self, context: Dict[str, Any]) -> str:
        """Format debate topic, agenda, outcomes"""
        
        parts = [f"📊 DEBATE: {context.get('title', 'Topic')}"]
        
        if context.get('description'):
            parts.append(f"Problem: {context['description']}")
        
        if context.get('agenda'):
            parts.append("Agenda:\n" + "\n".join(f"  - {item}" for item in context['agenda']))
        
        if context.get('desired_outcomes'):
            parts.append("Goals:\n" + "\n".join(f"  - {item}" for item in context['desired_outcomes']))
        
        return "\n\n".join(parts)
