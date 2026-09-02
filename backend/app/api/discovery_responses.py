from backend.app.api.schemas import (
    DiscoveryArticleResponse,
    DiscoveryPlantResponse,
    DiscoverySourceResponse,
    PublicDiscoveryArticleResponse,
)
from backend.app.models.encyclopedia import DiscoveryArticle


def discovery_article_response(article: DiscoveryArticle) -> DiscoveryArticleResponse:
    review = article.reviews[0] if article.reviews else None
    values = dict(
        id=article.id,
        slug=article.slug,
        status=article.status,
        headline=article.headline,
        standfirst=article.standfirst,
        body_blocks=article.body_blocks,
        limitations=article.limitations,
        safety_context=article.safety_context,
        cannot_conclude=article.cannot_conclude,
        qa_payload=article.qa_payload,
        version=article.version,
        content_origin=article.content_origin,
        article_type=article.article_type,
        research_date=article.research_date,
        research_question=article.research_question,
        research_context=article.research_context,
        study_design=article.study_design,
        evidence_base=article.evidence_base,
        intervention=article.intervention,
        comparator=article.comparator,
        main_findings=article.main_findings,
        evidence_strength=article.evidence_strength,
        evidence_strength_rationale=article.evidence_strength_rationale,
        why_matters=article.why_matters,
        practical_interpretation=article.practical_interpretation,
        section_sources=article.section_sources,
        hero_image=article.hero_image,
        geography=article.geography,
        linked_plants=[
            DiscoveryPlantResponse(
                id=link.plant_profile.id,
                slug=link.plant_profile.slug,
                common_name=link.plant_profile.display_common_name,
                scientific_name=link.plant_profile.accepted_scientific_name,
            )
            for link in article.plant_links
        ],
        category=article.event.category,
        relevance_reasons=article.event.reasons,
        detected_entities=article.event.detected_entities,
        evidence_package=article.event.evidence_package,
        sources=[
            DiscoverySourceResponse(
                id=link.source_record.id,
                pmid=link.source_record.external_identifier,
                doi=link.source_record.doi,
                canonical_url=link.source_record.canonical_url,
                title=link.source_record.title,
                authors=link.source_record.authors,
                journal=link.source_record.journal,
                publication_date=link.source_record.source_publication_date,
            )
            for link in article.sources
        ],
        review_id=review.id if review else None,
        review_status=review.status if review else None,
        reviewer_name=review.reviewer_name if review else None,
        decision_reason=review.decision_reason if review else None,
        created_at=article.created_at,
        reviewed_at=article.reviewed_at,
        published_at=article.published_at,
    )
    return DiscoveryArticleResponse(**values)


def public_discovery_article_response(
    article: DiscoveryArticle,
) -> PublicDiscoveryArticleResponse:
    if article.published_at is None:
        raise ValueError("Only published discoveries have a public response.")
    admin = discovery_article_response(article)
    return PublicDiscoveryArticleResponse(
        **admin.model_dump(
            include={
                "id",
                "slug",
                "headline",
                "standfirst",
                "body_blocks",
                "limitations",
                "safety_context",
                "cannot_conclude",
                "version",
                "article_type",
                "research_date",
                "research_question",
                "research_context",
                "study_design",
                "evidence_base",
                "intervention",
                "comparator",
                "main_findings",
                "evidence_strength",
                "evidence_strength_rationale",
                "why_matters",
                "practical_interpretation",
                "section_sources",
                "hero_image",
                "geography",
                "linked_plants",
                "category",
                "sources",
                "created_at",
            }
        ),
        published_at=article.published_at,
    )
