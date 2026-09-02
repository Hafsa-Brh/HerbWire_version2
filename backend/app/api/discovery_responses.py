from backend.app.api.schemas import (
    DiscoveryArticleResponse,
    DiscoverySourceResponse,
    PublicDiscoveryArticleResponse,
)
from backend.app.models.encyclopedia import DiscoveryArticle


def discovery_article_response(article: DiscoveryArticle) -> DiscoveryArticleResponse:
    review = article.reviews[0] if article.reviews else None
    return DiscoveryArticleResponse(
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


def public_discovery_article_response(
    article: DiscoveryArticle,
) -> PublicDiscoveryArticleResponse:
    if article.published_at is None:
        raise ValueError("Only published discoveries have a public response.")
    admin = discovery_article_response(article)
    return PublicDiscoveryArticleResponse(
        id=admin.id,
        slug=admin.slug,
        headline=admin.headline,
        standfirst=admin.standfirst,
        body_blocks=admin.body_blocks,
        limitations=admin.limitations,
        safety_context=admin.safety_context,
        cannot_conclude=admin.cannot_conclude,
        version=admin.version,
        category=admin.category,
        sources=admin.sources,
        created_at=admin.created_at,
        published_at=article.published_at,
    )
