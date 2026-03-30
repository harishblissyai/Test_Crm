"""
Pydantic schemas for Auth endpoints.

Request  → what the client sends in the body
Response → what the API returns (never includes password_hash)
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ── Requests ───────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None
    is_operator: bool = False
    # When creating an operator, Super Admin specifies which tenant they belong to
    tenant_id: UUID | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Responses ──────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    is_super_admin: bool
    is_operator: bool
    tenant_id: UUID | None
    client_id: UUID | None
    role_id: str | None
