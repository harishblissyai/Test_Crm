"""
Custom ASGI middleware.

RequestIDMiddleware  — attaches a unique UUID to every request.
TenantMiddleware     — decodes the JWT (if present) and populates
                       request.state with tenant/user context.
                       Does NOT raise errors — auth validation is
                       handled by the get_current_user dependency.
"""

import logging
import uuid

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates a UUID for each request.
    - Stored on request.state.request_id
    - Returned in the X-Request-ID response header
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Reads the Authorization header, decodes the JWT (without raising errors),
    and populates request.state with:
        tenant_id      — str | None
        user_id        — str | None
        role_id        — str | None
        is_super_admin — bool
        is_operator    — bool

    Routes that require auth use the get_current_user dependency,
    which will raise 401 if the token is missing or invalid.
    This middleware only pre-populates state for convenience
    (e.g., logging, non-auth middleware that needs tenant context).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Safe defaults
        request.state.tenant_id = None
        request.state.user_id = None
        request.state.role_id = None
        request.state.is_super_admin = False
        request.state.is_operator = False

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            try:
                from app.core.security import decode_access_token
                payload = decode_access_token(token)
                request.state.user_id = payload.get("sub")
                request.state.tenant_id = payload.get("tenant_id")
                request.state.role_id = payload.get("role_id")
                request.state.is_super_admin = payload.get("is_super_admin", False)
                request.state.is_operator = payload.get("is_operator", False)
            except JWTError:
                pass  # Invalid token — dependency will handle the 401

        return await call_next(request)
