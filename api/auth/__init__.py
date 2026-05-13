"""JWT token issuance and validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from policy import User


# Tiny in-memory user database. In production this would be Keycloak, Auth0,
# a real DB, etc. The point of this project is to demonstrate the flow, not
# to build an auth provider.
DEV_USERS: dict[str, dict[str, Any]] = {
    "admin": {
        "password": "admin",
        "role": "admin",
        "sub": "u-admin-001",
    },
    "alice": {
        "password": "alice",
        "role": "analyst",
        "sub": "u-alice-002",
    },
    "bob": {
        "password": "bob",
        "role": "user",
        "sub": "u-bob-003",
    },
}


class JWTManager:
    def __init__(self, secret: str, algorithm: str, expires_minutes: int) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.expires = timedelta(minutes=expires_minutes)

    def issue(self, sub: str, username: str, role: str) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        exp = now + self.expires
        payload = {
            "sub": sub,
            "username": username,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "type": "access",
        }
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, int(self.expires.total_seconds())

    def verify(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


_manager = JWTManager(
    secret=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    expires_minutes=settings.access_token_expire_minutes,
)


def get_jwt_manager() -> JWTManager:
    return _manager


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    record = DEV_USERS.get(username)
    if not record or record["password"] != password:
        return None
    return record


bearer_scheme = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = _manager.verify(creds.credentials)
    return User(
        sub=claims.get("sub", ""),
        username=claims.get("username", ""),
        role=claims.get("role", "user"),
        claims=claims,
    )
