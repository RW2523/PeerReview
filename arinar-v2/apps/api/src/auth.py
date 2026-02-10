"""Supabase Auth JWT validation and authorization"""
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header
from .config import settings


class AuthError(Exception):
    """Authentication/authorization error"""
    pass


def decode_jwt(token: str) -> Dict[str, Any]:
    """
    Decode and validate Supabase JWT token
    
    Args:
        token: JWT token from Authorization header
    
    Returns:
        Decoded token payload with user_id, workspace_id, tenant_id
    
    Raises:
        AuthError: Invalid token
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode JWT with Supabase secret
        # Disable iat verification to avoid clock skew issues
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=['HS256'],
            options={'verify_exp': True, 'verify_iat': False}
        )
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidSignatureError:
        raise AuthError("Invalid token signature")
    except jwt.DecodeError:
        raise AuthError("Invalid token format")
    except Exception as e:
        raise AuthError(f"Token validation failed: {str(e)}")


def get_workspace_for_user(user_id: str) -> Optional[str]:
    """
    Resolve workspace_id for user from user_workspaces table
    
    Args:
        user_id: Supabase user ID
    
    Returns:
        workspace_id or None if user not mapped to any workspace
    """
    from .database import get_db_connection, get_cursor
    
    try:
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute("""
                SELECT workspace_id, role
                FROM user_workspaces
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                return result['workspace_id']
            
            return None
    except Exception:
        # If DB query fails, return None (will be handled by caller)
        return None


def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Extract and validate current user from JWT
    
    Args:
        authorization: Authorization header value
    
    Returns:
        User info dict with user_id, workspace_id, tenant_id
    
    Raises:
        HTTPException: 401 if token missing/invalid
    """
    if not settings.require_auth:
        # Auth disabled for local dev/testing
        return {
            'user_id': 'test-user',
            'workspace_id': '00000000-0000-0000-0000-000000000101',
            'tenant_id': '00000000-0000-0000-0000-000000000001'
        }
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = decode_jwt(authorization)
        
        # Extract user context from JWT payload
        user_id = payload.get('sub')  # Supabase user ID
        workspace_id = payload.get('workspace_id')
        tenant_id = payload.get('tenant_id')
        
        if not user_id:
            raise AuthError("Token missing user ID (sub)")
        
        # If workspace_id not in JWT, resolve from user_workspaces table
        if not workspace_id:
            workspace_id = get_workspace_for_user(user_id)
        
        return {
            'user_id': user_id,
            'workspace_id': workspace_id,
            'tenant_id': tenant_id,
            'email': payload.get('email'),
            'role': payload.get('role')
        }
    
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


def check_workspace_access(
    user: Dict[str, Any],
    resource_workspace_id: str
) -> None:
    """
    Verify user has access to workspace
    
    Args:
        user: User context from JWT
        resource_workspace_id: Workspace ID of requested resource
    
    Raises:
        HTTPException: 403 if user lacks access
    """
    user_workspace_id = user.get('workspace_id')
    
    if not user_workspace_id:
        # No workspace claim in token - deny access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any workspace"
        )
    
    if user_workspace_id != resource_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: debate belongs to different workspace"
        )


def require_auth(authorization: str = Header(None)) -> str:
    """
    Convenience dependency for routes that just need workspace_id
    
    Args:
        authorization: Authorization header value
    
    Returns:
        workspace_id string
    
    Raises:
        HTTPException: 401 if token missing/invalid
    """
    user = get_current_user(authorization)
    workspace_id = user.get('workspace_id')
    
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any workspace"
        )
    
    return workspace_id
