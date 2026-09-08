import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
