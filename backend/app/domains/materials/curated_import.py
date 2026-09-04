from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from backend.app.domains.materials.corpus import CuratedMaterialCorpus
from backend.app.models.encyclopedia import SourceRecord
from backend.app.models.materials import MaterialStory, MaterialStorySource
from backend.app.models.source import Source
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class MaterialImportSummary:
    created: int
    unchanged: int
    source_records_created: int
    source_links_created: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_media(story) -> None:
    relative = story.hero_media.local_path.removeprefix("/")
    path = Path(__file__).resolve().parents[4] / "frontend" / "public" / relative
    if not path.is_file():
        raise ValueError(f"Licensed media is missing for {story.slug}.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != story.hero_media.checksum_sha256:
        raise ValueError(f"Licensed media checksum differs for {story.slug}.")


def _registry_source(session: Session, item, now: datetime) -> Source:
    source = session.scalar(select(Source).where(Source.identifier == item.provider))
    if source is not None:
        return source
    parsed = urlsplit(str(item.canonical_url))
    source = Source(
        identifier=item.provider,
        name=item.institution,
        base_url=f"{parsed.scheme}://{parsed.netloc}",
        status="active",
        created_at=now,
        updated_at=now,
    )
    session.add(source)
    session.flush()
    return source


def _source_record(
    session: Session, source: Source, item, now: datetime
) -> tuple[SourceRecord, bool]:
    external_identifier = item.source_id.split(":", 1)[1]
    existing = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_id == source.id,
            SourceRecord.external_identifier == external_identifier,
        )
    )
    if existing is not None:
        if (
            existing.canonical_url != str(item.canonical_url)
            or existing.title != item.title
        ):
            raise ValueError(f"Existing material source differs for {item.source_id}.")
        return existing, False
    payload = item.model_dump(mode="json")
    record = SourceRecord(
        source_id=source.id,
        external_identifier=external_identifier,
        url=str(item.canonical_url),
        canonical_url=str(item.canonical_url),
        title=item.title,
        publisher=item.institution,
        source_type=item.source_type,
        original_language="en",
        license_status="Linked institutional source; source terms remain applicable.",
        supports={"materials": True, "provider": item.provider, "curated": True},
        permitted_extract=None,
        parser_version="curated-material-source-v1",
        content_hash=hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        source_publication_date=item.publication_date,
        doi=None,
        authors=[],
        journal=None,
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record, True


def import_curated_materials(
    session: Session, corpus: CuratedMaterialCorpus
) -> MaterialImportSummary:
    for item in corpus.stories:
        _validate_media(item)
        existing = session.scalar(
            select(MaterialStory).where(MaterialStory.slug == item.slug)
        )
        if (
            existing is not None
            and existing.content_version == item.content_version
            and existing.content_checksum != item.content_checksum
        ):
            raise ValueError(
                f"Refusing changed same-version material content for {item.slug}."
            )
        if existing is not None and existing.content_version != item.content_version:
            raise ValueError(f"Refusing to overwrite material version for {item.slug}.")
    created = unchanged = source_records_created = source_links_created = 0
    now = _now()
    try:
        for item in corpus.stories:
            existing = session.scalar(
                select(MaterialStory).where(MaterialStory.slug == item.slug)
            )
            if existing is not None:
                unchanged += 1
                continue
            story = MaterialStory(
                id=UUID(item.id),
                slug=item.slug,
                content_version=item.content_version,
                content_checksum=item.content_checksum,
                title=item.title,
                deck=item.deck,
                category=item.category,
                material_labels=item.material_labels,
                geography_label=item.geography_label,
                sections=[section.model_dump(mode="json") for section in item.sections],
                reading_time_minutes=item.reading_time_minutes,
                status="published",
                featured=item.featured,
                sort_order=item.sort_order,
                hero_media=item.hero_media.model_dump(mode="json"),
                published_at=datetime.fromisoformat(
                    item.published_at.replace("Z", "+00:00")
                ),
                created_at=now,
                updated_at=now,
            )
            session.add(story)
            session.flush()
            for source_item in item.sources:
                source = _registry_source(session, source_item, now)
                record, was_created = _source_record(session, source, source_item, now)
                session.add(
                    MaterialStorySource(
                        material_story_id=story.id,
                        source_record_id=record.id,
                        support_role=source_item.source_type,
                        supported_sections=[
                            section.key
                            for section in item.sections
                            if source_item.source_id in section.source_ids
                        ],
                    )
                )
                source_records_created += int(was_created)
                source_links_created += 1
            created += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return MaterialImportSummary(
        created, unchanged, source_records_created, source_links_created
    )
