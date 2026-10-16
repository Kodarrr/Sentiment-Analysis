import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FeedbackCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=5000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    user_id: str
    text: str
    status: str
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    sentiment_polarity: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] | None = None
    model_id: str | None = None
    model_revision: str | None = None
    retry_count: int
    created_at: datetime
    processed_at: datetime | None = None


class PaginatedFeedbackResponse(BaseModel):
    items: list[FeedbackResponse]
    total: int
    page: int
    page_size: int


class SentimentTrendPoint(BaseModel):
    date: date
    positive_count: int
    negative_count: int
    neutral_count: int = 0


class SentimentDistributionResponse(BaseModel):
    labels: dict[str, int]
    polarities: dict[str, int]
    total: int



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
