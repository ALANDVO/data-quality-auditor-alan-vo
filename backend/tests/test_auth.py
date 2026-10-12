import pytest
from fastapi import HTTPException
from app.core.config import Settings
from app.core.auth import (
    create_demo_token,
    decode_token,
    get_current_user,
    require_role,
    UserProfile,
)

def test_auth_demo_token_generation_and_decode():
    token = create_demo_token(username="analyst_test", role="analyst")
    decoded = decode_token(token)
    assert decoded["preferred_username"] == "analyst_test"
    assert "analyst" in decoded["roles"]

def test_auth_role_denial():
    # User with viewer role attempting analyst action
    viewer_user = UserProfile(id="1", username="viewer1", roles=["viewer"])
    analyst_checker = require_role("analyst")
    with pytest.raises(HTTPException) as exc_info:
        analyst_checker(viewer_user)
    assert exc_info.value.status_code == 403
    assert "Insufficient privileges" in exc_info.value.detail or "requires 'analyst'" in exc_info.value.detail

def test_auth_role_hierarchy_admin_allowed_as_analyst():
    admin_user = UserProfile(id="1", username="admin1", roles=["admin"])
    analyst_checker = require_role("analyst")
    # Admin has analyst rights through role hierarchy
    res = analyst_checker(admin_user)
    assert res.username == "admin1"

def test_auth_missing_credentials():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401

def test_demo_mode_refused_in_production():
    with pytest.raises(RuntimeError):
        # Initializing settings with ENVIRONMENT=production and DEMO_MODE=true must raise
        Settings(ENVIRONMENT="production", DEMO_MODE=True)
