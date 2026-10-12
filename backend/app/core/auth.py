import time
from typing import List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from app.core.config import settings
from app.models.schemas import UserProfile

security_scheme = HTTPBearer(auto_error=False)

# Role hierarchy: admin has analyst & viewer; analyst has viewer
ROLE_HIERARCHY = {
    "admin": ["admin", "analyst", "viewer"],
    "analyst": ["analyst", "viewer"],
    "viewer": ["viewer"],
}

DEMO_USERS = {
    "demo-admin": {"username": "demo-admin", "email": "admin@demo.local", "roles": ["admin"]},
    "demo-analyst": {"username": "demo-analyst", "email": "analyst@demo.local", "roles": ["analyst"]},
    "demo-viewer": {"username": "demo-viewer", "email": "viewer@demo.local", "roles": ["viewer"]},
}

def create_demo_token(username: str, role: str) -> str:
    """Generate a valid signed demo JWT for local testing and demo mode."""
    if not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError("Demo tokens are disabled in production mode")
    secret = settings.JWT_SECRET or "local-dev-demo-secret-key-do-not-use-in-prod"
    payload = {
        "sub": f"usr-{username}",
        "preferred_username": username,
        "email": f"{username}@demo.local",
        "iss": settings.OIDC_ISSUER_URL,
        "aud": settings.OIDC_AUDIENCE,
        "realm_access": {"roles": [role]},
        "roles": [role],
        "exp": int(time.time()) + 86400,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_token(token_str: str) -> dict:
    """Validate and decode JWT token with issuer and audience checks."""
    secret = settings.JWT_SECRET or "local-dev-demo-secret-key-do-not-use-in-prod"
    
    # Try decoding with configured secret/demo secret first
    try:
        payload = jwt.decode(
            token_str,
            secret,
            algorithms=["HS256", "RS256"],
            issuer=settings.OIDC_ISSUER_URL,
            audience=settings.OIDC_AUDIENCE,
            options={"verify_signature": True, "verify_aud": True, "verify_iss": True},
        )
        return payload
    except JWTError:
        pass

    # If in local demo mode, also accept unverified decode only if explicit DEMO_MODE is on
    if settings.DEMO_MODE and settings.ENVIRONMENT.lower() != "production":
        try:
            payload = jwt.decode(
                token_str,
                "",
                options={"verify_signature": False, "verify_aud": False, "verify_iss": False},
            )
            return payload
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token signature",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> UserProfile:
    """Extract and validate user identity from Authorization Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = credentials.credentials

    # Special demo shorthand token for convenience in local testing if demo mode active
    if settings.DEMO_MODE and settings.ENVIRONMENT.lower() != "production":
        if token_str in DEMO_USERS:
            u = DEMO_USERS[token_str]
            return UserProfile(
                id=f"usr-{token_str}",
                username=u["username"],
                email=u["email"],
                roles=u["roles"],
            )

    payload = decode_token(token_str)
    user_id = payload.get("sub", "unknown")
    username = payload.get("preferred_username") or payload.get("name") or user_id
    email = payload.get("email")

    # Extract roles from Keycloak standard locations
    roles: List[str] = []
    if "realm_access" in payload and isinstance(payload["realm_access"], dict):
        roles.extend(payload["realm_access"].get("roles", []))
    if "roles" in payload and isinstance(payload["roles"], list):
        roles.extend(payload["roles"])

    # Normalise roles (lowercase, deduplicate)
    roles = list(set(r.lower() for r in roles if isinstance(r, str)))
    if not roles:
        roles = ["viewer"]

    return UserProfile(id=str(user_id), username=str(username), email=email, roles=roles)

def require_role(required_role: str):
    """Enforce minimum role requirement based on role hierarchy."""
    def role_checker(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        allowed = False
        for user_role in user.roles:
            effective_roles = ROLE_HIERARCHY.get(user_role, [user_role])
            if required_role in effective_roles:
                allowed = True
                break
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires '{required_role}' privilege",
            )
        return user
    return role_checker

require_viewer = require_role("viewer")
require_analyst = require_role("analyst")
require_admin = require_role("admin")
