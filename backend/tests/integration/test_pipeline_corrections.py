import uuid

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.discovery.pipeline_catalog import (
    load_discovery_pipeline_catalog,
)
from backend.app.domains.encyclopedia.plant_eligibility import (
    check_subject_eligibility,
    subject_from_discovery_candidate,
)
from backend.app.domains.pipeline.discovery_article_pipeline import (
    execute_run_to_terminal,
    preview_candidates,
    start_run,
)
from backend.app.models.encyclopedia import (
    DiscoveryPipelineItem,
    EditorialReview,
    PipelineBotanicalReservation,
    PipelineRun,
    PlantProfile,
)
from sqlalchemy import func, select, text


@pytest.fixture(autouse=True)
def clean_tables():
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE pipeline_botanical_reservations, discovery_pipeline_items, "
                "plant_pipeline_items, pipeline_stage_results, pipeline_runs, "
                "editorial_reviews, plant_profile_revisions, plant_profile_sources, "
                "discovery_article_plants, discovery_article_sources, "
                "discovery_articles, discovery_events, source_records, "
                "plant_profiles CASCADE"
            )
        )
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )


def test_full_discovery_batch_leaves_ten_and_next_rejection_writes_nothing():
    with get_session_factory()() as session:
        assert preview_candidates(session, 10)["available_count"] == 20
        run = start_run(session, 10, str(uuid.uuid4()))
        run_id, owner = run.id, run.lease_owner
    execute_run_to_terminal(run_id, owner)
    with get_session_factory()() as session:
        preview = preview_candidates(session, 1)
        assert preview["available_count"] == 10
        assert preview["can_start"] is False
        before = (
            session.scalar(select(func.count()).select_from(PipelineRun)),
            session.scalar(select(func.count()).select_from(DiscoveryPipelineItem)),
            session.scalar(
                select(func.count()).select_from(PipelineBotanicalReservation)
            ),
            session.scalar(select(func.count()).select_from(EditorialReview)),
        )
        with pytest.raises(ValueError, match="protected editorial reserve"):
            start_run(session, 1, str(uuid.uuid4()))
        after = (
            session.scalar(select(func.count()).select_from(PipelineRun)),
            session.scalar(select(func.count()).select_from(DiscoveryPipelineItem)),
            session.scalar(
                select(func.count()).select_from(PipelineBotanicalReservation)
            ),
            session.scalar(select(func.count()).select_from(EditorialReview)),
        )
        assert after == before


def test_private_plant_profile_blocks_discovery_subject_without_scanning_prose():
    candidate = load_discovery_pipeline_catalog().candidates[0]
    subject = candidate.primary_botanical_subject
    profile = PlantProfile(
        slug="private-beetroot",
        status="needs_review",
        accepted_scientific_name=subject.accepted_scientific_name,
        botanical_author=subject.botanical_author,
        taxon_identifier=subject.taxon_identifier,
        known_synonyms=subject.synonyms,
        display_common_name=subject.common_names[0],
        family_name="Amaranthaceae",
        summary="Private structured profile fixture.",
        introduction="Private structured profile fixture.",
        botanical_description="Private structured profile fixture.",
        traditional_uses=[],
        parts_used=[],
        distribution=[],
        preparation="No preparation advice.",
        safety_notes=[],
        evidence_notes="No efficacy claim.",
        article_details={"incidental_prose": "This prose mentions unrelated cocoa."},
        hero_image={},
    )
    with get_session_factory()() as session:
        session.add(profile)
        session.commit()
        result = check_subject_eligibility(
            session, subject_from_discovery_candidate(candidate)
        )
        assert not result.eligible
        assert result.reason_code == "represented_botanical_subject"
        assert preview_candidates(session, 10)["available_count"] == 19


def test_all_available_is_bounded_to_runnable_capacity_above_reserve():
    with get_session_factory()() as session:
        preview = preview_candidates(session, 1, all_available=True)
        assert preview["available_count"] == 20
        assert preview["planned_count"] == 10
        run = start_run(session, 1, str(uuid.uuid4()), all_available=True)
        assert len(run.discovery_items) == 10
