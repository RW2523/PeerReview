"""AI assistance endpoints for improving user input"""
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional
import httpx
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ProblemStatementRequest(BaseModel):
    input_text: str


class ProblemStatementResponse(BaseModel):
    improved_text: str
    key_points: list[str]
    agenda_items: list[str]
    desired_outcomes: list[str]


@router.post("/ai/improve-problem-statement", response_model=ProblemStatementResponse)
async def improve_problem_statement(
    request: ProblemStatementRequest,
    x_openrouter_key: Optional[str] = Header(None, alias="X-OpenRouter-Key")
):
    """
    Improve a problem statement for debate using AI.
    Uses cost-effective Claude Haiku model.
    """
    if not x_openrouter_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key required (X-OpenRouter-Key header)"
        )
    
    if not request.input_text or len(request.input_text.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text must be at least 10 characters"
        )
    
    # Use Claude Haiku - very cost effective (~$0.25 per 1M input tokens)
    model = "anthropic/claude-3-haiku"
    
    system_prompt = """You are an expert at structuring multi-agent debates and meetings.

Your task: Take the user's rough problem statement and create a complete debate structure including:
1. An improved, debate-worthy problem statement
2. Key discussion points
3. Meeting agenda items
4. Desired outcomes

Guidelines:
- Make the problem statement clear, concise, and specific (under 200 words)
- Frame it as a question or problem with multiple valid perspectives
- Create 3-5 key discussion points
- Suggest 3-4 agenda items for the meeting
- Define 2-3 desired outcomes

STRICT OUTPUT FORMAT (you MUST follow this exactly):
```
PROBLEM STATEMENT:
[Write the improved problem statement here]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]

AGENDA:
- [Agenda item 1]
- [Agenda item 2]
- [Agenda item 3]

DESIRED OUTCOMES:
- [Outcome 1]
- [Outcome 2]
```

Example:
Input: "we need to figure out what to do about sales"
Output:
```
PROBLEM STATEMENT:
How should our organization restructure its sales strategy to achieve 30% growth in Q2 while maintaining customer satisfaction and team morale?

KEY POINTS:
- Revenue growth targets and timeline
- Customer experience and retention
- Sales team capacity and motivation
- Resource allocation and budgeting
- Market conditions and competition

AGENDA:
- Review current sales performance and identify gaps
- Discuss proposed strategies and resource requirements
- Evaluate impact on team and customers
- Create action plan with ownership and timelines

DESIRED OUTCOMES:
- Agreement on specific growth strategy with measurable targets
- Clear action plan with assigned responsibilities
- Commitment to maintaining customer satisfaction scores above 8.5/10
```"""
    
    user_prompt = f"""Create a complete debate structure for this topic:

"{request.input_text}"

Remember to follow the EXACT format with all four sections: PROBLEM STATEMENT, KEY POINTS, AGENDA, and DESIRED OUTCOMES."""
    
    try:
        # Retry logic for rate limits
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {x_openrouter_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "max_tokens": 800,
                            "temperature": 0.7,
                        }
                    )
                    
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limited (429), retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="AI service rate limit exceeded. Please try again in a moment."
                            )
                    
                    if response.status_code != 200:
                        logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"AI service error: {response.status_code}"
                        )
                    
                    result = response.json()
                    ai_output = result["choices"][0]["message"]["content"]
                    break  # Success, exit retry loop
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise
            
        # Parse the structured output
        improved_text = ""
        key_points = []
        agenda_items = []
        desired_outcomes = []
        
        # Extract sections
        sections = {
            "PROBLEM STATEMENT:": "improved_text",
            "KEY POINTS:": "key_points",
            "AGENDA:": "agenda_items",
            "DESIRED OUTCOMES:": "desired_outcomes"
        }
        
        current_section = None
        current_content = []
        
        for line in ai_output.split('\n'):
            line = line.strip()
            
            # Check if this is a section header
            section_found = False
            for header, var_name in sections.items():
                if header in line:
                    # Save previous section
                    if current_section:
                        if current_section == "improved_text":
                            improved_text = '\n'.join(current_content).strip()
                        else:
                            # Extract bullet points
                            items = [
                                l.lstrip('-').lstrip('•').lstrip('*').strip()
                                for l in current_content
                                if l and (l.startswith('-') or l.startswith('•') or l.startswith('*'))
                            ]
                            if current_section == "key_points":
                                key_points = items
                            elif current_section == "agenda_items":
                                agenda_items = items
                            elif current_section == "desired_outcomes":
                                desired_outcomes = items
                    
                    current_section = var_name
                    current_content = []
                    section_found = True
                    break
            
            if not section_found and current_section and line:
                current_content.append(line)
        
        # Save last section
        if current_section:
            if current_section == "improved_text":
                improved_text = '\n'.join(current_content).strip()
            else:
                items = [
                    l.lstrip('-').lstrip('•').lstrip('*').strip()
                    for l in current_content
                    if l and (l.startswith('-') or l.startswith('•') or l.startswith('*'))
                ]
                if current_section == "key_points":
                    key_points = items
                elif current_section == "agenda_items":
                    agenda_items = items
                elif current_section == "desired_outcomes":
                    desired_outcomes = items
        
        # Fallback if parsing failed
        if not improved_text:
            improved_text = ai_output.strip()
        
        return ProblemStatementResponse(
            improved_text=improved_text,
            key_points=key_points,
            agenda_items=agenda_items,
            desired_outcomes=desired_outcomes
        )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to AI service"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to improve problem statement: {str(e)}"
        )
