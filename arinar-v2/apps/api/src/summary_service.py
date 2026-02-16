"""Summary generation service for M3 end-of-meeting outputs"""
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import psycopg2.extras
from .database import get_db_connection, get_cursor
from .openrouter_client import OpenRouterClient


class SummaryService:
    """
    Service for generating and storing debate summaries (M3)
    
    Generates:
    - Summary (short, 1-3 sentences)
    - Minutes (detailed meeting recap)
    - Action items (structured list)
    """
    
    def __init__(self, openrouter_client: Optional[OpenRouterClient] = None):
        self.client = openrouter_client
    
    def generate_summary(
        self,
        debate_id: str,
        openrouter_api_key: str,
        model_id: str = "openai/gpt-4o-mini"  # Cost-optimized: $0.15/$0.60 (was $3/$15!)
    ) -> Dict[str, Any]:
        """
        Generate summary/minutes/action items for a debate
        
        Args:
            debate_id: Debate UUID
            openrouter_api_key: OpenRouter BYOK key (never stored)
            model_id: Model to use for generation
        
        Returns:
            Dict with summary, minutes, action_items
        
        Raises:
            ValueError: Debate not found or not ended
            RuntimeError: OpenRouter error
        """
        # Get debate and events
        debate = self._get_debate(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")
        
        if debate['state'] != 'ended':
            raise ValueError(f"Debate must be ended to generate summary (current state: {debate['state']})")
        
        events = self._get_events(debate_id)
        
        # Build context from events
        context = self._build_context(debate, events)
        
        # Generate via OpenRouter
        client = self.client or OpenRouterClient(api_key=openrouter_api_key)
        
        prompt = self._build_summary_prompt(context)
        response = client.chat_completion(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000  # Increased to avoid truncation
        )
        
        # Parse structured output
        outputs = self._parse_summary_response(response['content'])
        
        # Store in database
        self._save_outputs(
            debate_id=debate_id,
            summary=outputs['summary'],
            minutes=outputs['minutes'],
            action_items=outputs['action_items'],
            model_used=model_id,
            token_count=response.get('usage', {}).get('total_tokens')
        )
        
        # Create event in ledger
        self._create_summary_event(debate_id, outputs)
        
        return outputs
    
    def get_summary(self, debate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get existing summary for a debate
        
        Returns:
            Dict with summary/minutes/action_items or None if not generated
        """
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                SELECT 
                    output_id, debate_id, summary, minutes, action_items,
                    generated_at, model_used, token_count, created_at
                FROM debate_outputs
                WHERE debate_id = %s
            """, (debate_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _get_debate(self, debate_id: str) -> Optional[Dict[str, Any]]:
        """Get debate details"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                SELECT debate_id, workspace_id, title, description, state, created_at
                FROM debates
                WHERE debate_id = %s
            """, (debate_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _get_events(self, debate_id: str) -> List[Dict[str, Any]]:
        """Get all events for debate"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                SELECT 
                    event_id, event_type, sender_type, sequence_number,
                    content, created_at
                FROM events
                WHERE debate_id = %s
                ORDER BY sequence_number ASC
            """, (debate_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _build_context(self, debate: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
        """Build context string from debate and events"""
        lines = [
            f"# Debate: {debate['title']}",
            f"Description: {debate.get('description', 'N/A')}",
            f"",
            "## Events:",
            ""
        ]
        
        for event in events:
            event_type = event['event_type']
            content = event.get('content', {})
            
            if event_type == 'system_message':
                action = content.get('action', 'unknown')
                lines.append(f"- System: {action}")
            elif event_type == 'intervention':
                text = content.get('text', '')
                tagged = content.get('tagged_agents', [])
                lines.append(f"- Intervention: {text} (tagged: {', '.join(tagged)})")
            elif event_type in ['agent_message', 'debate_turn']:
                text = content.get('text', content.get('message', ''))
                lines.append(f"- {event['sender_type']}: {text[:200]}...")
        
        return "\n".join(lines)
    
    def _build_summary_prompt(self, context: str) -> str:
        """Build prompt for summary generation"""
        return f"""You are analyzing a debate meeting. Generate a structured summary in JSON format.

{context}

**CRITICAL**: You MUST output ONLY valid, complete JSON. No markdown, no code blocks, no explanations.

Output this EXACT JSON structure (fill in the content):

{{
  "summary": "Write 1-3 sentence high-level summary here",
  "minutes": "Write detailed meeting minutes here (2-4 paragraphs covering key points, decisions, and disagreements)",
  "action_items": [
    {{"description": "Specific action item", "owner": "Role or person responsible", "priority": "high"}},
    {{"description": "Another action item", "owner": "Owner name", "priority": "medium"}}
  ]
}}

Requirements:
- Summary: Concise, captures main outcome and decisions
- Minutes: Comprehensive, covers what was discussed and decided
- Action items: Specific, actionable tasks with clear ownership and priority (high/medium/low)
- MUST be valid, complete JSON - ensure all quotes are closed, all braces are matched
- If no action items identified, use empty array: "action_items": []

START YOUR RESPONSE WITH {{ and END WITH }}"""
    
    def _parse_summary_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured outputs"""
        import re
        
        # Try multiple parsing strategies
        
        # Strategy 1: Direct JSON parse
        try:
            parsed = json.loads(content)
            
            # Validate structure
            if not all(k in parsed for k in ['summary', 'minutes', 'action_items']):
                raise ValueError("Missing required keys in summary response")
            
            return {
                'summary': parsed['summary'],
                'minutes': parsed['minutes'],
                'action_items': parsed['action_items']
            }
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse failed: {str(e)}")
            pass
        
        # Strategy 2: Extract from markdown code block
        try:
            if '```json' in content:
                json_str = content.split('```json')[1].split('```')[0].strip()
                parsed = json.loads(json_str)
                return {
                    'summary': parsed['summary'],
                    'minutes': parsed['minutes'],
                    'action_items': parsed['action_items']
                }
            elif '```' in content:
                # Try generic code block
                json_str = content.split('```')[1].split('```')[0].strip()
                parsed = json.loads(json_str)
                return {
                    'summary': parsed['summary'],
                    'minutes': parsed['minutes'],
                    'action_items': parsed['action_items']
                }
        except (json.JSONDecodeError, IndexError) as e:
            print(f"⚠️ Markdown extraction failed: {str(e)}")
            pass
        
        # Strategy 3: Try to fix incomplete JSON
        try:
            # If JSON is incomplete, try to close it
            content_cleaned = content.strip()
            if content_cleaned.startswith('{') and not content_cleaned.endswith('}'):
                # Add missing closing braces
                open_count = content_cleaned.count('{')
                close_count = content_cleaned.count('}')
                content_cleaned += '}' * (open_count - close_count)
                
                # Also close any open arrays
                open_arrays = content_cleaned.count('[')
                close_arrays = content_cleaned.count(']')
                if open_arrays > close_arrays:
                    content_cleaned = content_cleaned.rstrip(',') + ']' * (open_arrays - close_arrays)
                
                parsed = json.loads(content_cleaned)
                
                return {
                    'summary': parsed.get('summary', 'Summary generation incomplete'),
                    'minutes': parsed.get('minutes', 'Minutes generation incomplete'),
                    'action_items': parsed.get('action_items', [])
                }
        except Exception as e:
            print(f"⚠️ JSON repair failed: {str(e)}")
            pass
        
        # Strategy 4: Fallback to extracting text manually
        print(f"⚠️ All parsing strategies failed. Creating fallback summary...")
        return {
            'summary': 'Summary generation failed - unable to parse AI response',
            'minutes': f'The AI generated an invalid response format. Raw content (first 500 chars):\n\n{content[:500]}',
            'action_items': []
        }
    
    def _save_outputs(
        self,
        debate_id: str,
        summary: str,
        minutes: str,
        action_items: List[Dict[str, Any]],
        model_used: str,
        token_count: Optional[int]
    ) -> None:
        """Save outputs to debate_outputs table"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                INSERT INTO debate_outputs (
                    debate_id, summary, minutes, action_items,
                    generated_at, model_used, token_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (debate_id) 
                DO UPDATE SET
                    summary = EXCLUDED.summary,
                    minutes = EXCLUDED.minutes,
                    action_items = EXCLUDED.action_items,
                    generated_at = EXCLUDED.generated_at,
                    model_used = EXCLUDED.model_used,
                    token_count = EXCLUDED.token_count,
                    updated_at = NOW()
            """, (
                debate_id,
                summary,
                minutes,
                psycopg2.extras.Json(action_items),
                datetime.now(timezone.utc),
                model_used,
                token_count
            ))
    
    def _create_summary_event(self, debate_id: str, outputs: Dict[str, Any]) -> None:
        """Create debate_summary event in events ledger"""
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # Get next sequence number
            cursor.execute("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_seq
                FROM events
                WHERE debate_id = %s
            """, (debate_id,))
            next_seq = cursor.fetchone()['next_seq']
            
            # Create event
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO events (
                    event_id, debate_id, event_type, sender_type,
                    sequence_number, content, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                debate_id,
                'debate_summary',
                'system',
                next_seq,
                psycopg2.extras.Json({
                    'summary': outputs['summary'],
                    'action_item_count': len(outputs['action_items'])
                }),
                datetime.now(timezone.utc)
            ))
