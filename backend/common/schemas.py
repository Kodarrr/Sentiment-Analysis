import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FeedbackCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=5000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: str
    text: str
    status: str
    sentiment_label: str | None
    sentiment_score: float | None
    retry_count: int
    created_at: datetime
    processed_at: datetime | None


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
