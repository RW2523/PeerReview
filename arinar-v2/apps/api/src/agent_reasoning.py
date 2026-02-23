"""
Agent Reasoning Module - Stage 1 of Constitutional AI Pipeline

Anthropic-inspired: Before generating a response, the agent first
reasons about their stance, what's changed, and how to respond.

This is Claude's "thinking before speaking" approach.
"""
import json
from typing import Dict, Any, Optional
from .openrouter_client import OpenRouterClient


class AgentReasoningEngine:
    """
    Stage 1: Evaluates agent's current stance against new information
    
    Outputs structured reasoning that feeds into response generation.
    """
    
    def __init__(self, openrouter_api_key: str):
        self.client = OpenRouterClient(openrouter_api_key)
    
    def evaluate_stance(
        self,
        agent_name: str,
        agent_role: str,
        past_positions: str,
        recent_conversation: str,
        user_intervention: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Agent thinks through their position before responding
        
        Args:
            agent_name: Agent's name
            agent_role: Agent's role description (e.g., "Professional Arguer")
            past_positions: Summary of agent's past messages
            recent_conversation: Last 3-5 messages from others
            user_intervention: Any moderator input
        
        Returns:
            {
                "current_stance": "one sentence position",
                "confidence": 0.0-1.0,
                "stance_changed": bool,
                "reason_for_change": "explanation or null",
                "key_points": ["point1", "point2", "point3"],
                "should_disagree_with": ["agent_name"] or []
            }
        """
        
        prompt = self._build_reasoning_prompt(
            agent_name,
            agent_role,
            past_positions,
            recent_conversation,
            user_intervention
        )
        
        try:
            response = self.client.chat_completion(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an internal reasoning engine. Output ONLY valid JSON. Think step-by-step about the agent's position."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,  # Lower temp for reasoning
                max_tokens=400
            )
            
            reasoning = json.loads(response["content"])
            
            # Validate structure
            required_keys = ["current_stance", "confidence", "stance_changed", "key_points"]
            if not all(key in reasoning for key in required_keys):
                raise ValueError(f"Missing required keys in reasoning output: {reasoning.keys()}")
            
            # Check for repetition (enterprise safeguard)
            if reasoning.get("am_i_repeating") == "repeat":
                print(f"    ⚠️ REPETITION DETECTED in reasoning stage")
                print(f"    What others said: {reasoning.get('what_others_said', 'N/A')[:100]}")
                print(f"    Agent is repeating, not adding new info")
            
            return reasoning
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse reasoning JSON: {e}")
            # Fallback to safe default
            return {
                "current_stance": "maintain previous position",
                "confidence": 0.7,
                "stance_changed": False,
                "reason_for_change": None,
                "key_points": ["continue previous argument"],
                "should_disagree_with": []
            }
        except Exception as e:
            print(f"⚠️ Reasoning engine error: {e}")
            return {
                "current_stance": "maintain previous position",
                "confidence": 0.7,
                "stance_changed": False,
                "reason_for_change": None,
                "key_points": ["continue previous argument"],
                "should_disagree_with": []
            }
    
    def _build_reasoning_prompt(
        self,
        agent_name: str,
        agent_role: str,
        past_positions: str,
        recent_conversation: str,
        user_intervention: Optional[str]
    ) -> str:
        """Build the reasoning prompt (topic-agnostic)"""
        
        intervention_text = ""
        if user_intervention:
            intervention_text = f"""
🎙️ MODERATOR/USER JUST SAID:
{user_intervention}

⚠️ CRITICAL: Don't automatically agree. Evaluate objectively.
"""
        
        return f"""You are the internal reasoning system for {agent_name} ({agent_role}).

{past_positions}

RECENT CONVERSATION:
{recent_conversation}

{intervention_text}

TASK: Think step-by-step about your position.

STEP 1: What's your current stance? (one clear sentence)
STEP 2: What's your confidence? (0.0 to 1.0)
STEP 3: Has your stance changed since your last message? (true/false)
STEP 4: If changed, why? What NEW evidence/reasoning justifies it?
STEP 5: What did others JUST say in recent conversation? (1 sentence summary)
STEP 6: Am I about to REPEAT what they said, or add NEW information? (repeat/new/build_on)
STEP 7: What are my 3 UNIQUE points that others haven't made yet?
STEP 8: Should you disagree with anyone? (list agent names or [])

CRITICAL - AVOID REPETITION:
- If others just said "X needs actionable policies", DON'T say "X needs specific policies"
- If others said "Y is popular with youth", DON'T say "Y appeals to young voters"
- EITHER: Add NEW data/reasoning, OR disagree and explain why they're wrong
- Your unique_contribution must be DIFFERENT from what others just said

RULES FOR STANCE CHANGES:
- If moderator asks "what about X?", evaluate X objectively - don't auto-switch to X
- Only change stance if NEW data/reasoning genuinely contradicts your position
- If you change stance, you MUST explain why in "reason_for_change"
- If you're a contrarian role (Professional Arguer, Devil's Advocate), default to disagreeing

OUTPUT (valid JSON only):
{{
  "current_stance": "one sentence",
  "confidence": 0.85,
  "stance_changed": false,
  "reason_for_change": null,
  "what_others_said": "summary of recent points from others",
  "am_i_repeating": "repeat/new/build_on",
  "unique_contribution": "what I'm adding that's NEW",
  "key_points": ["point 1", "point 2", "point 3"],
  "should_disagree_with": []
}}"""
    
    def check_flip_flop(
        self,
        past_stance: Optional[str],
        new_stance: str,
        justification: Optional[str]
    ) -> Dict[str, Any]:
        """
        Detect if agent is flip-flopping without good reason
        
        Returns:
            {
                "is_flip_flop": bool,
                "severity": "none" | "minor" | "major",
                "warning": "explanation"
            }
        """
        if not past_stance:
            return {"is_flip_flop": False, "severity": "none", "warning": None}
        
        # Simple heuristic: if stance changed but no justification
        if past_stance.lower() != new_stance.lower():
            if not justification or len(justification.strip()) < 20:
                return {
                    "is_flip_flop": True,
                    "severity": "major",
                    "warning": "Agent changed stance without explaining why"
                }
            else:
                return {
                    "is_flip_flop": False,
                    "severity": "minor",
                    "warning": "Stance changed but justified"
                }
        
        return {"is_flip_flop": False, "severity": "none", "warning": None}
