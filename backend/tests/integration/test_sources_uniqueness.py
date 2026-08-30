import uuid
from datetime import datetime, timezone

import pytest
from backend.app.db.session import get_engine
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def test_sources_identifier_uniqueness_constraint_is_enforced() -> None:
    engine = get_engine()
    identifier = f"integration-source-{uuid.uuid4()}"
    created_at = datetime.now(timezone.utc)

    with engine.connect() as connection:
        table_name = connection.execute(
            text("SELECT to_regclass('public.sources')")
        ).scalar_one()
        assert table_name == "sources"

    insert_sql = text(
        """
        INSERT INTO sources (
            id,
            identifier,
            name,
            base_url,
            status,
            created_at,
            updated_at
        )
        VALUES (
            :id,
            :identifier,
            :name,
            :base_url,
            :status,
            :created_at,
            :updated_at
        )
        """
    )

    with engine.begin() as connection:
        connection.execute(
            insert_sql,
            {
                "id": uuid.uuid4(),
                "identifier": identifier,
                "name": "Integration Source",
                "base_url": "https://example.test/source",
                "status": "proposed",
                "created_at": created_at,
                "updated_at": created_at,
            },
        )

    try:
        with engine.begin() as connection:
            connection.execute(
                insert_sql,
                {
                    "id": uuid.uuid4(),
                    "identifier": identifier,
                    "name": "Duplicate Integration Source",
                    "base_url": "https://example.test/duplicate-source",
                    "status": "proposed",
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )
    except IntegrityError as error:
        message = str(error.orig)
        assert (
            "uq_sources_identifier" in message
            or "duplicate key value violates unique constraint" in message
        )
    else:
        pytest.fail("Duplicate source identifier insert unexpectedly succeeded.")
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM sources WHERE identifier = :identifier"),
                {"identifier": identifier},
            )
