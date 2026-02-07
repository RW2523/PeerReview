"""OpenRouter integration endpoints"""
from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional, Dict, Any
import httpx
from ..openrouter_models_service import fetch_openrouter_models
from ..schemas.openrouter import ModelListResponse, OpenRouterModel

router = APIRouter()


@router.get("/openrouter/models", response_model=ModelListResponse)
async def list_openrouter_models(
    x_openrouter_key: Optional[str] = Header(None, alias="X-OpenRouter-Key")
):
    """
    Fetch OpenRouter model catalog using user's BYOK key.
    
    Key is never stored - only used for this request.
    Results are cached in-memory for 60s per key hash.
    
    Headers:
        X-OpenRouter-Key: <openrouter-api-key>
    
    Returns:
        List of available models
    
    Raises:
        400: Missing or invalid API key
        401: OpenRouter authentication failed
        500: OpenRouter API error
    """
    if not x_openrouter_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key required in X-OpenRouter-Key header"
        )
    
    api_key = x_openrouter_key.strip()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key is empty"
        )
    
    try:
        models = await fetch_openrouter_models(api_key)
        return ModelListResponse(
            models=[OpenRouterModel(**m) for m in models],
            cached=False  # TODO(TICKET-08C.2B): track cache status from service layer
        )
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OpenRouter API key"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenRouter API error: {e.response.status_code}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch models: {str(e)}"
        )


@router.get("/openrouter/account")
async def get_openrouter_account(
    x_openrouter_key: Optional[str] = Header(None, alias="X-OpenRouter-Key")
) -> Dict[str, Any]:
    """
    Get OpenRouter account info: usage, limits, credits.
    
    Uses user's BYOK key to fetch account details from OpenRouter.
    Key is never stored.
    
    Headers:
        X-OpenRouter-Key: <openrouter-api-key>
    
    Returns:
        Account info including key usage, limits, rate limits, and credits (if available)
    
    Raises:
        400: Missing API key
        401: Invalid API key
        500: OpenRouter API error
    """
    if not x_openrouter_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key required in X-OpenRouter-Key header"
        )
    
    api_key = x_openrouter_key.strip()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key is empty"
        )
    
    async with httpx.AsyncClient() as client:
        try:
            # Fetch key info (usage, limits, rate limits)
            key_response = await client.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            key_response.raise_for_status()
            key_data = key_response.json()
            
            # Try to fetch credits (requires management key, may fail)
            credits_data = None
            note = None
            
            try:
                credits_response = await client.get(
                    "https://openrouter.ai/api/v1/credits",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                credits_response.raise_for_status()
                credits_data = credits_response.json()
            
            except httpx.HTTPStatusError as credits_error:
                if credits_error.response.status_code == 403:
                    note = "Credits endpoint requires management key. Showing usage/limits only."
                else:
                    note = f"Could not fetch credits: {credits_error.response.status_code}"
            
            except Exception as credits_error:
                note = f"Could not fetch credits: {str(credits_error)}"
            
            return {
                "key": key_data.get("data", {}),
                "credits": credits_data.get("data") if credits_data else None,
                "note": note
            }
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OpenRouter API key"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenRouter API error: {e.response.status_code}"
            )
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch account info: {str(e)}"
            )
