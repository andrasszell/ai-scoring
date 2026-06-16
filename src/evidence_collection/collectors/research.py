from __future__ import annotations

from ..dates import normalize_publication_year
from ..config import settings
from ..db import repository as repo
from ..extraction import content_hash
from ..http import get
from ..models import CollectionContext, CollectorResult
from ..status import CollectionStatus
from ..universe.entity import clean_company_name
from .base import Collector

SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1/paper/search"


class ResearchCollector(Collector):
    """AI research-paper evidence via Semantic Scholar (works unauthenticated,
    but is heavily rate-limited; an API key raises the limits)."""

    name = "research"
    platform_id = "semantic_scholar"
    version = "1.0.0"
    source_type = "research_paper"
    source_name = "Semantic Scholar"

    def collect(self, ctx: CollectionContext, company: dict, *, limit: int = 10) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        name = clean_company_name(company.get("company_name", ""))
        query = f'"{name}" artificial intelligence machine learning'
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,year,abstract,url,authors,venue,citationCount",
        }
        headers = {"x-api-key": settings.semantic_scholar_api_key} if settings.semantic_scholar_api_key else None
        try:
            resp = get(SEMANTIC_SCHOLAR, params=params, headers=headers)
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            status = CollectionStatus.RATE_LIMITED if "429" in str(exc) else CollectionStatus.SOURCE_UNAVAILABLE
            return CollectorResult(status, message=f"error: {exc}")

        repo.save_raw_response(
            conn, ticker=ticker, source_type=self.source_type, collector_name=self.name,
            collector_version=self.version, request_url=SEMANTIC_SCHOLAR, request_params=query,
            status_code=getattr(resp, "status_code", None), response_text=resp.text[:200_000],
            content_hash=content_hash(resp.text),
        )

        repo.delete_evidence(conn, ticker, self.name)
        rows = []
        for p in data.get("data", []):
            title = p.get("title") or ""
            if not title:
                continue
            abstract = p.get("abstract") or ""
            source_date, date_provenance = normalize_publication_year(p.get("year"))
            rows.append(
                self.make_evidence(
                    company,
                    evidence_text=f"{title}. {abstract[:1200]}",
                    source_url=p.get("url"),
                    source_date=source_date,
                    evidence_title=title,
                    metadata={
                        "venue": p.get("venue"),
                        "citationCount": p.get("citationCount"),
                        "date_provenance": date_provenance,
                    },
                )
            )
        inserted = repo.insert_evidence(conn, rows)
        status = CollectionStatus.SUCCESS if inserted else CollectionStatus.NO_RESULTS
        return CollectorResult(status, evidence_count=inserted, api_calls=1)
