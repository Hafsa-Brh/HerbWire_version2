"""Automatic recovery for persisted editorial generation runs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from backend.app.db.session import get_session_factory
from backend.app.models.encyclopedia import PipelineRun, utc_now
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

LOGGER = logging.getLogger(__name__)
EDITORIAL_PIPELINE_TYPES = (
    "plant_profile_automation",
    "discovery_article_automation",
)
LEASE_SECONDS = 120
RECOVERY_POLL_SECONDS = 5.0


@dataclass(frozen=True)
class RecoveryClaim:
    run_id: UUID
    pipeline_type: str
    lease_owner: str


def claim_recoverable_run(session: Session) -> RecoveryClaim | None:
    """Claim one expired active run and reset only its incomplete stage boundary."""
    now = utc_now()
    run = session.scalar(
        select(PipelineRun)
        .options(
            selectinload(PipelineRun.stages),
            selectinload(PipelineRun.plant_items),
            selectinload(PipelineRun.discovery_items),
        )
        .where(
            PipelineRun.pipeline_type.in_(EDITORIAL_PIPELINE_TYPES),
            PipelineRun.status == "running",
            or_(
                PipelineRun.lease_expires_at.is_(None),
                PipelineRun.lease_expires_at <= now,
            ),
        )
        .order_by(PipelineRun.started_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if run is None:
        return None

    running_stages = [stage for stage in run.stages if stage.status == "running"]
    for stage in running_stages:
        stage.status = "pending"
        stage.attempt += 1
        stage.started_at = None
        stage.completed_at = None
        stage.duration_ms = 0
        stage.error_code = None
        stage.error_message = "Recovered after an interrupted web process."
    items = (
        run.plant_items
        if run.pipeline_type == "plant_profile_automation"
        else run.discovery_items
    )
    for item in items:
        if item.status == "running":
            item.status = "pending"
            item.error_code = None
            item.error_message = None
            item.completed_at = None

    owner = uuid4().hex
    run.lease_owner = owner
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    run.finished_at = None
    run.summary = {
        **run.summary,
        "automatic_recovery_count": int(run.summary.get("automatic_recovery_count", 0))
        + 1,
    }
    session.commit()
    return RecoveryClaim(run.id, run.pipeline_type, owner)


def execute_claim(claim: RecoveryClaim) -> None:
    if claim.pipeline_type == "plant_profile_automation":
        from backend.app.domains.pipeline.plant_profile_pipeline import (
            execute_run_to_terminal,
        )
    else:
        from backend.app.domains.pipeline.discovery_article_pipeline import (
            execute_run_to_terminal,
        )
    execute_run_to_terminal(claim.run_id, claim.lease_owner)


def recover_once() -> bool:
    factory = get_session_factory()
    with factory() as session:
        claim = claim_recoverable_run(session)
    if claim is None:
        return False
    execute_claim(claim)
    return True


async def recovery_supervisor(stop: asyncio.Event) -> None:
    """Recover stale work while this single web process remains alive."""
    while not stop.is_set():
        try:
            recovered = await asyncio.to_thread(recover_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.warning("Editorial pipeline recovery check failed safely.")
            recovered = False
        if recovered:
            continue
        try:
            await asyncio.wait_for(stop.wait(), timeout=RECOVERY_POLL_SECONDS)
        except TimeoutError:
            pass
