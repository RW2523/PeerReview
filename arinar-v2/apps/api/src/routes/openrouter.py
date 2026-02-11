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
    x_openrouter_key: Optional[str] = Header(None, alias="X-OpenRouter-Key"),
    x_openrouter_management_key: Optional[str] = Header(None, alias="X-OpenRouter-Management-Key")
) -> Dict[str, Any]:
    """
    Get OpenRouter account info: usage, limits, credits.
    
    Uses user's BYOK key to fetch account details from OpenRouter.
    Keys are never stored.
    
    Headers:
        X-OpenRouter-Key: <openrouter-api-key> (required - for validation)
        X-OpenRouter-Management-Key: <management-key> (optional - for credits)
    
    Returns:
        Account info including key validation, models available, and credits (if management key provided)
    
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
    management_key = x_openrouter_management_key.strip() if x_openrouter_management_key else None
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key is empty"
        )
    
    async with httpx.AsyncClient() as client:
        try:
            # Validate key by fetching models (works with all key types)
            models_response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            models_response.raise_for_status()
            models_data = models_response.json()
            model_count = len(models_data.get("data", []))
            
            # Try to fetch key info (requires management/dashboard key)
            key_data = None
            key_to_check = management_key if management_key else api_key
            
            try:
                key_response = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {key_to_check}"},
                    timeout=10.0
                )
                if key_response.status_code == 200:
                    key_data = key_response.json().get("data", {})
            except Exception as e:
                # Management endpoints not available for regular keys (expected)
                print(f"Key info endpoint unavailable: {e}")
            
            # Try to fetch credits (use management key if provided, otherwise try regular key)
            credits_data = None
            credits_balance = None
            
            if management_key:
                try:
                    credits_response = await client.get(
                        "https://openrouter.ai/api/v1/credits",
                        headers={"Authorization": f"Bearer {management_key}"},
                        timeout=10.0
                    )
                    if credits_response.status_code == 200:
                        credits_data = credits_response.json().get("data")
                        if credits_data:
                            # Calculate balance
                            total_credits = credits_data.get("total_credits", 0)
                            total_usage = credits_data.get("total_usage", 0)
                            credits_balance = total_credits - total_usage
                except Exception as e:
                    print(f"Credits endpoint error with management key: {e}")
            
            # Build response
            note = None
            if not management_key:
                note = "Add management API key to view credits balance."
            elif not credits_data:
                note = "Could not fetch credits. Check management key permissions."
            
            return {
                "key": key_data or {
                    "label": "API Key",
                    "is_valid": True,
                    "validated_via": "models_endpoint"
                },
                "credits": {
                    "total_credits": credits_data.get("total_credits") if credits_data else None,
                    "total_usage": credits_data.get("total_usage") if credits_data else None,
                    "balance": credits_balance
                } if credits_data else None,
                "models_available": model_count,
                "has_management_key": management_key is not None,
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
