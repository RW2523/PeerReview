"""Analytics endpoints for debate analysis"""
from fastapi import APIRouter, Header, HTTPException
from typing import Dict, Any, List
from ..database import get_db_connection, get_cursor

router = APIRouter()


@router.get("/debates/{debate_id}/analytics/autonomous-behaviors")
async def get_autonomous_behaviors(
    debate_id: str,
    authorization: str = Header(None)
):
    """Get all autonomous behaviors (coalitions, private messages) for a debate"""
    
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        try:
            # Get coalitions
            cursor.execute("""
                SELECT event_id, sequence_number, content, created_at
                FROM events
                WHERE debate_id = %s AND event_type = 'coalition_formed'
                ORDER BY sequence_number
            """, (debate_id,))
            
            coalitions = cursor.fetchall()
            
            # Get private messages
            cursor.execute("""
                SELECT event_id, sequence_number, content, created_at
                FROM events
                WHERE debate_id = %s AND event_type = 'private_message'
                ORDER BY sequence_number
            """, (debate_id,))
            
            private_messages = cursor.fetchall()
            
            # Get subtasks if any
            cursor.execute("""
                SELECT event_id, sequence_number, content, created_at
                FROM events
                WHERE debate_id = %s AND event_type = 'agent_subtask'
                ORDER BY sequence_number
            """, (debate_id,))
            
            subtasks = cursor.fetchall()
            
            return {
                "debate_id": debate_id,
                "coalitions": [{
                    "event_id": c['event_id'],
                    "sequence": c['sequence_number'],
                    "members": c['content'].get('members', []),
                    "type": c['content'].get('type', 'alliance'),
                    "strategy": c['content'].get('strategy'),
                    "formed_by": c['content'].get('formed_by'),
                    "timestamp": c['content'].get('timestamp'),
                    "created_at": c['created_at'].isoformat() if c['created_at'] else None
                } for c in coalitions],
                "private_messages": [{
                    "event_id": pm['event_id'],
                    "sequence": pm['sequence_number'],
                    "from_agent": pm['content'].get('from_agent'),
                    "to_agent": pm['content'].get('to_agent'),
                    "message": pm['content'].get('message'),
                    "timestamp": pm['content'].get('timestamp'),
                    "created_at": pm['created_at'].isoformat() if pm['created_at'] else None
                } for pm in private_messages],
                "subtasks": [{
                    "event_id": st['event_id'],
                    "sequence": st['sequence_number'],
                    "agent_name": st['content'].get('agent_name'),
                    "subtask": st['content'].get('subtask'),
                    "timestamp": st['content'].get('timestamp'),
                    "created_at": st['created_at'].isoformat() if st['created_at'] else None
                } for st in subtasks],
                "summary": {
                    "total_coalitions": len(coalitions),
                    "total_private_messages": len(private_messages),
                    "total_subtasks": len(subtasks),
                    "alliances": len([c for c in coalitions if c['content'].get('type') == 'alliance']),
                    "rivalries": len([c for c in coalitions if c['content'].get('type') == 'rivalry'])
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")
        finally:
            cursor.close()


@router.get("/debates/{debate_id}/analytics/scope-tracking")
async def get_scope_tracking(
    debate_id: str,
    authorization: str = Header(None)
):
    """Analyze if agents stayed on topic / met original goals"""
    
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        try:
            # Get debate goals
            cursor.execute("""
                SELECT title, desired_outcomes, agenda
                FROM debates
                WHERE debate_id = %s
            """, (debate_id,))
            
            debate = cursor.fetchone()
            
            if not debate:
                raise HTTPException(status_code=404, detail="Debate not found")
            
            # Get all agent messages
            cursor.execute("""
                SELECT sequence_number, content
                FROM events
                WHERE debate_id = %s AND event_type = 'agent_message'
                ORDER BY sequence_number
            """, (debate_id,))
            
            messages = cursor.fetchall()
            
            # Get host conclusion
            cursor.execute("""
                SELECT content
                FROM events
                WHERE debate_id = %s AND sender_type = 'host'
                ORDER BY sequence_number DESC
                LIMIT 1
            """, (debate_id,))
            
            host = cursor.fetchone()
            
            return {
                "debate_id": debate_id,
                "title": debate['title'],
                "desired_outcomes": debate['desired_outcomes'] or [],
                "agenda": debate['agenda'] or [],
                "message_count": len(messages),
                "has_host_conclusion": host is not None,
                "messages": [{
                    "sequence": m['sequence_number'],
                    "agent": m['content'].get('agent_name'),
                    "preview": m['content'].get('text', '')[:150]
                } for m in messages],
                "host_conclusion_preview": host['content'].get('text', '')[:500] if host else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch scope tracking: {str(e)}")
        finally:
            cursor.close()
