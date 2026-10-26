"""The Python service verifies credentials even when reached without the gateway."""

import os
import jwt
from fastapi import HTTPException, Request


def decode_user(token: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            os.getenv("JWT_SECRET", "nexus-ai-local-secret-key-2026-32chars!!"),
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        return {"id": int(claims["sub"]), "role": claims.get("role", "user")}
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(401, "登录凭证无效或已过期") from exc


def current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    return decode_user(auth[7:])
