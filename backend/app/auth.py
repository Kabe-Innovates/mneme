"""
Mneme JWT Authentication
========================
Server-issued JWT tokens with role claims. Shift-based 8-hour expiry.
Adopted from Divathiru's auth system (simplified for SQLite/hackathon).

Users are loaded from backend/data/users.json (synthetic — one per hospital role).
"""

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_JWT_SECRET = os.getenv("JWT_SECRET", "mneme-jwt-secret-change-in-production")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 8  # Shift-based: one full hospital shift

_security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# User Store (loaded from JSON)
# ---------------------------------------------------------------------------

_users: dict[str, dict] = {}
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load_users():
    global _users
    path = os.path.join(DATA_DIR, "users.json")
    if not os.path.exists(path):
        print("[Auth] users.json not found — generating synthetic users")
        _generate_users(path)
    with open(path) as f:
        user_list = json.load(f)
    _users = {u["user_id"]: u for u in user_list}
    print(f"[Auth] Loaded {len(_users)} users")


def _hash_password(password: str) -> str:
    """Simple SHA-256 hash for hackathon. Production: use bcrypt/argon2id."""
    return hashlib.sha256(password.encode()).hexdigest()


def _generate_users(path: str):
    """Generate one synthetic user per hospital role."""
    from app.models import HOSPITAL_ROLES

    users = []
    for i, role_name in enumerate(HOSPITAL_ROLES, 1):
        # Create a simple username from the role
        username = role_name.lower().replace(" & ", "_").replace(" ", "_")
        users.append({
            "user_id": f"USR-{i:03d}",
            "username": username,
            "name": f"{role_name} Staff",
            "role": role_name,
            "password_hash": _hash_password("mneme2024"),  # Default password
            "active": True,
        })
    # Add a supervisor/admin user
    users.append({
        "user_id": "USR-ADM",
        "username": "supervisor",
        "name": "Operations Supervisor",
        "role": "Operations Management",
        "password_hash": _hash_password("admin2024"),
        "active": True,
    })

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(users, f, indent=2)
    print(f"[Auth] Generated {len(users)} synthetic users at {path}")


# ---------------------------------------------------------------------------
# Token Management
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, role: str, name: str) -> str:
    """Create a JWT access token with role claims and shift-based expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "name": name,
        "iat": now,
        "exp": now + timedelta(hours=_JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises on invalid/expired."""
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


# ---------------------------------------------------------------------------
# Authentication Functions
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Verify username and password. Returns user dict or None."""
    if not _users:
        _load_users()

    password_hash = _hash_password(password)
    for user in _users.values():
        if user["username"] == username and user["password_hash"] == password_hash:
            if not user.get("active", True):
                return None
            return user
    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> dict:
    """FastAPI dependency: extract and validate the Bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    claims = decode_token(credentials.credentials)
    return {
        "user_id": claims["sub"],
        "role": claims["role"],
        "name": claims["name"],
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> Optional[dict]:
    """FastAPI dependency: returns user if authenticated, None otherwise."""
    if credentials is None:
        return None
    try:
        claims = decode_token(credentials.credentials)
        return {
            "user_id": claims["sub"],
            "role": claims["role"],
            "name": claims["name"],
        }
    except HTTPException:
        return None


# Load users on import
_load_users()
