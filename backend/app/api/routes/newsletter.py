import re

from backend.app.api.schemas import (
    NewsletterSubscriptionRequest,
    NewsletterSubscriptionResponse,
)
from backend.app.db.session import get_session
from backend.app.models.encyclopedia import NewsletterSubscription
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette import status

router = APIRouter(prefix="/newsletter")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if not EMAIL_PATTERN.fullmatch(normalized) or len(normalized) > 320:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid email address.",
        )
    return normalized


@router.post("/subscriptions", response_model=NewsletterSubscriptionResponse)
def create_subscription(
    request: NewsletterSubscriptionRequest, session: Session = Depends(get_session)
) -> NewsletterSubscriptionResponse:
    email = normalize_email(request.email)
    existing = session.scalar(
        select(NewsletterSubscription).where(NewsletterSubscription.email == email)
    )
    if existing is not None:
        return NewsletterSubscriptionResponse(
            email=existing.email,
            status="already_subscribed",
            created_at=existing.created_at,
        )

    subscription = NewsletterSubscription(email=email)
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return NewsletterSubscriptionResponse(
        email=subscription.email,
        status="subscribed",
        created_at=subscription.created_at,
    )
