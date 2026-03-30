"""
Custom ASGI middleware.

RequestIDMiddleware  — attaches a unique UUID to every request.
TenantMiddleware     — placeholder; Module 2 (Auth) will decode the JWT
                       and populate request.state.tenant_id here.
"""

import logging
import uuid

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
        # Use caller-supplied ID if present, otherwise generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts tenant context from the incoming request.

    Currently a pass-through — Module 2 (Auth) will extend this to
    decode the JWT and set:
        request.state.tenant_id
        request.state.user_id
        request.state.role_id
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Initialise state so downstream code can always read these safely
        request.state.tenant_id = None
        request.state.user_id = None
        request.state.role_id = None

        response = await call_next(request)
        return response
