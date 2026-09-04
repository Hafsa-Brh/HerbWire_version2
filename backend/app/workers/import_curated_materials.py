from backend.app.db.session import get_session_factory
from backend.app.domains.materials.corpus import load_curated_material_corpus
from backend.app.domains.materials.curated_import import import_curated_materials


def main() -> None:
    with get_session_factory()() as session:
        summary = import_curated_materials(session, load_curated_material_corpus())
    print(
        f"created={summary.created} unchanged={summary.unchanged} "
        f"sources={summary.source_records_created} "
        f"links={summary.source_links_created}"
    )


if __name__ == "__main__":
    main()
