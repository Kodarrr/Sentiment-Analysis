from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status
from rq import Queue
from sqlalchemy.orm import Session

from backend.common.db import get_db
from backend.common.models import Feedback
from backend.common.queue import get_queue
from backend.common.schemas import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackCreate,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    queue: Annotated[Queue, Depends(get_queue)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Feedback:
    if idempotency_key:
        existing = (
            db.query(Feedback).filter(Feedback.idempotency_key == idempotency_key).first()
        )
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing

    feedback = Feedback(
        user_id=payload.user_id,
        text=payload.text,
        idempotency_key=idempotency_key,
        status="pending",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    queue.enqueue("backend.worker.tasks.process_feedback", str(feedback.id))

    response.status_code = status.HTTP_201_CREATED
    return feedback
