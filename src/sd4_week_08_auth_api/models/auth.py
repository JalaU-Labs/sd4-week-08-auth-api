from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(
        description="Email address associated with the local account.",
        examples=["alice@example.com"],
    )
    password: str = Field(
        min_length=1,
        max_length=128,
        description="Password for the local account.",
        examples=["StrongPass123!"],
    )


class TokenResponse(BaseModel):
    access_token: str = Field(
        description="Opaque local session token. Use it as a Bearer token for protected routes.",
        examples=["opaque-session-token"],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type used in the Authorization header.",
        examples=["bearer"],
    )
    expires_in: int = Field(
        description="Token lifetime in seconds.",
        examples=[3600],
    )
