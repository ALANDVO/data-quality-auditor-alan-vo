from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.config import settings
from app.core.auth import get_current_user, create_demo_token, DEMO_USERS
from app.models.schemas import UserProfile

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/me", response_model=UserProfile)
def get_me(user: UserProfile = Depends(get_current_user)):
    """Retrieve identity and roles for the authenticated user."""
    return user

@router.get("/config")
def get_auth_config() -> Dict[str, Any]:
    """Retrieve public OIDC client configuration and demo mode status."""
    return {
        "oidc_issuer_url": settings.OIDC_ISSUER_URL,
        "oidc_audience": settings.OIDC_AUDIENCE,
        "demo_mode": settings.DEMO_MODE,
        "environment": settings.ENVIRONMENT,
        "supported_roles": ["admin", "analyst", "viewer"],
    }

@router.post("/demo-token")
def generate_demo_token(role: str = Query("analyst", pattern="^(admin|analyst|viewer)$")) -> Dict[str, str]:
    """Generate a test bearer token for the specified role in local demo mode."""
    if not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo token issuance is disabled in production environments.",
        )
    username = f"demo-{role}"
    token = create_demo_token(username=username, role=role)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "username": username,
        "role": role,
    }
