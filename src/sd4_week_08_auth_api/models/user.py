from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(
        description="Email address for the new account.",
        examples=["alice@example.com"],
    )
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Desired username: 3-32 letters, numbers, or underscores.",
        examples=["alice"],
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password for the new account; must contain 8-128 characters.",
        examples=["StrongPass123!"],
    )


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description="Unique identifier assigned to the user.",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    email: EmailStr = Field(
        description="User's email address.",
        examples=["alice@example.com"],
    )
    username: str = Field(
        description="User's public username.",
        examples=["alice"],
    )
    is_active: bool = Field(
        description="Whether the account is active and can authenticate.",
        examples=[True],
    )
    created_at: datetime = Field(
        description="UTC timestamp when the account was created.",
        examples=["2026-11-24T12:00:00Z"],
    )


class UserInDB(UserPublic):
    hashed_password: str
