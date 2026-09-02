from datetime import datetime

from backend.app.domains.discovery.contracts import NormalizedDiscoveryRecord
from backend.app.models.encyclopedia import SourceRecord
from backend.app.models.source import Source
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

PUBMED_SOURCE_IDENTIFIER = "pubmed-eutils"
PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"


def require_pubmed_source(session: Session) -> Source:
    source = session.scalar(
        select(Source).where(Source.identifier == PUBMED_SOURCE_IDENTIFIER)
    )
    if source is None:
        raise RuntimeError("The approved PubMed source registry entry is missing.")
    if source.status != "approved" or source.base_url != PUBMED_BASE_URL:
        raise RuntimeError("The PubMed source registry entry is not approved.")
    return source


def find_duplicate(
    session: Session, source: Source, record: NormalizedDiscoveryRecord
) -> SourceRecord | None:
    existing = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_id == source.id,
            SourceRecord.external_identifier == record.external_identifier,
        )
    )
    if existing is not None:
        return existing
    if record.doi:
        existing = session.scalar(
            select(SourceRecord).where(SourceRecord.doi == record.doi)
        )
        if existing is not None:
            return existing
    existing = session.scalar(
        select(SourceRecord).where(SourceRecord.canonical_url == record.canonical_url)
    )
    if existing is not None:
        return existing
    return session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_id == source.id,
            SourceRecord.content_hash == record.content_hash,
        )
    )


def get_or_create_source_record(
    session: Session,
    source: Source,
    record: NormalizedDiscoveryRecord,
    now: datetime,
) -> tuple[SourceRecord, bool]:
    existing = find_duplicate(session, source, record)
    if existing is not None:
        return existing, False

    record_id = session.scalar(
        insert(SourceRecord)
        .values(
            source_id=source.id,
            external_identifier=record.external_identifier,
            url=record.canonical_url,
            canonical_url=record.canonical_url,
            title=record.title,
            publisher="National Library of Medicine (PubMed)",
            source_type="scientific_literature",
            original_language=record.original_language,
            license_status=(
                "PubMed metadata; abstract copyright remains with its holder."
            ),
            supports={
                "discovery": True,
                "provider": "pubmed",
                "pmid": record.external_identifier,
                "metadata": record.metadata,
            },
            permitted_extract=record.abstract,
            parser_version="pubmed-efetch-v1",
            content_hash=record.content_hash,
            source_publication_date=record.publication_date,
            doi=record.doi,
            authors=list(record.authors),
            journal=record.journal,
            collected_at=datetime.fromisoformat(record.collected_at_iso),
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing()
        .returning(SourceRecord.id)
    )
    if record_id is not None:
        return session.get_one(SourceRecord, record_id), True
    duplicate = find_duplicate(session, source, record)
    if duplicate is None:
        raise RuntimeError("Source record conflict could not be resolved safely.")
    return duplicate, False
