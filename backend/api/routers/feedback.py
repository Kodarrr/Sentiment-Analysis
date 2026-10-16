import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from rq import Queue
from rq.job import Callback
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.models import AdminUser, Feedback
from backend.common.queue import get_queue, get_retry_policy
from backend.common.rate_limit import feedback_rate_limit, limiter
from backend.common.schemas import (
    FeedbackCreate,
    FeedbackResponse,
    PaginatedFeedbackResponse,
    SentimentDistributionResponse,
    SentimentTrendPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit(feedback_rate_limit)
def submit_feedback(
    request: Request,
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
            logger.info(
                "idempotent feedback replay",
                extra={"feedback_id": str(existing.id), "idempotency_key": idempotency_key},
            )
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

    queue.enqueue(
        "backend.worker.tasks.process_feedback",
        str(feedback.id),
        retry=get_retry_policy(),
        on_failure=Callback("backend.worker.tasks.handle_job_failure"),
    )

    logger.info(
        "feedback submitted",
        extra={"feedback_id": str(feedback.id), "user_id": feedback.user_id},
    )

    response.status_code = status.HTTP_201_CREATED
    return feedback


@router.get("/feedback", response_model=PaginatedFeedbackResponse)
def list_feedback(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[AdminUser, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sentiment: Annotated[str | None, Query()] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> PaginatedFeedbackResponse:
    query = db.query(Feedback)
    if sentiment:
        s_upper = sentiment.upper()
        s_lower = sentiment.lower()
        query = query.filter(
            or_(
                Feedback.sentiment_label == s_upper,
                Feedback.sentiment_polarity == s_lower,
            )
        )
    if start_date:
        query = query.filter(Feedback.created_at >= start_date)
    if end_date:
        query = query.filter(Feedback.created_at < end_date + timedelta(days=1))

    total = query.count()
    items = (
        query.order_by(Feedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedFeedbackResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/feedback/stats/trend", response_model=list[SentimentTrendPoint])
def sentiment_trend(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[AdminUser, Depends(get_current_user)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> list[SentimentTrendPoint]:
    day = func.date(Feedback.created_at).label("day")
    query = db.query(
        day,
        func.sum(
            case(
                (
                    or_(
                        Feedback.sentiment_polarity == "positive",
                        Feedback.sentiment_label == "POSITIVE",
                    ),
                    1,
                ),
                else_=0,
            )
        ).label("positive"),
        func.sum(
            case(
                (
                    or_(
                        Feedback.sentiment_polarity == "negative",
                        Feedback.sentiment_label == "NEGATIVE",
                    ),
                    1,
                ),
                else_=0,
            )
        ).label("negative"),
        func.sum(
            case(
                (
                    or_(
                        Feedback.sentiment_polarity == "neutral",
                        Feedback.sentiment_label == "NU",
                    ),
                    1,
                ),
                else_=0,
            )
        ).label("neutral"),
    )
    if start_date:
        query = query.filter(Feedback.created_at >= start_date)
    if end_date:
        query = query.filter(Feedback.created_at < end_date + timedelta(days=1))

    rows = query.group_by(day).order_by(day).all()

    return [
        SentimentTrendPoint(
            date=row.day,
            positive_count=row.positive or 0,
            negative_count=row.negative or 0,
            neutral_count=row.neutral or 0,
        )
        for row in rows
    ]


@router.get("/feedback/stats/distribution", response_model=SentimentDistributionResponse)
def sentiment_distribution(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[AdminUser, Depends(get_current_user)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> SentimentDistributionResponse:
    query = db.query(Feedback)
    if start_date:
        query = query.filter(Feedback.created_at >= start_date)
    if end_date:
        query = query.filter(Feedback.created_at < end_date + timedelta(days=1))

    label_rows = (
        query.with_entities(Feedback.sentiment_label, func.count(Feedback.id))
        .group_by(Feedback.sentiment_label)
        .all()
    )
    polarity_rows = (
        query.with_entities(Feedback.sentiment_polarity, func.count(Feedback.id))
        .group_by(Feedback.sentiment_polarity)
        .all()
    )

    labels = {str(r[0]): int(r[1]) for r in label_rows if r[0]}
    polarities = {str(r[0]): int(r[1]) for r in polarity_rows if r[0]}
    total = query.count()

    return SentimentDistributionResponse(labels=labels, polarities=polarities, total=total)

