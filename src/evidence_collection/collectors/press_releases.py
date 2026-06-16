from __future__ import annotations

from urllib.parse import urlparse

from ..config import settings
from ..dates import collection_date_iso, web_result_date
from ..db import repository as repo
from ..extraction import keyword_hits
from ..http import get
from ..models import CollectionContext, CollectorResult, collector_result
from ..outcomes import OutcomeReason
from ..registry_gate import api_key_missing_result
from ..status import CollectionStatus
from ..universe.entity import search_name
from .base import Collector
from .serpapi import AI_TERMS, SERPAPI, _save_raw

PRESS_TERMS = '("press release" OR press OR announces OR announcement OR "news release")'


def build_press_query(company: dict, *, conn) -> str:
    """Compose a SerpAPI query biased toward corporate press releases."""
    domain = (company.get("website_domain") or "").strip().lower().removeprefix("www.")
    if domain:
        return f"site:{domain} ({AI_TERMS}) {PRESS_TERMS}"
    name = search_name(company, conn=conn)
    return f'"{name}" ({AI_TERMS}) {PRESS_TERMS}'


def parse_press_rows(
    collector,
    company: dict,
    query: str,
    organic_results: list[dict],
    *,
    retrieval_date: str | None = None,
) -> list[dict]:
    """Turn SerpAPI organic results into press-release evidence rows (pure, testable)."""
    retrieval = retrieval_date or collection_date_iso()
    rows: list[dict] = []
    for result in organic_results:
        text = " — ".join(x for x in [result.get("title"), result.get("snippet")] if x)
        if not text or not keyword_hits(text):
            continue
        source_date, date_provenance = web_result_date(result, fallback=retrieval)
        rows.append(
            collector.make_evidence(
                company,
                evidence_text=text,
                source_url=result.get("link"),
                source_date=source_date,
                evidence_title=result.get("title"),
                metadata={
                    "query": query,
                    "domain": urlparse(result.get("link", "")).netloc,
                    "date_provenance": date_provenance,
                    "keywords": keyword_hits(text),
                },
            )
        )
    return rows


class PressReleasesCollector(Collector):
    """Corporate press releases mentioning AI via SerpAPI Google web search.

    When ``website_domain`` is known, the query is restricted to the company site
    for higher-precision first-party announcements; otherwise falls back to name search.
    """

    name = "press_releases"
    platform_id = "press_releases"
    version = "1.0.0"
    source_type = "press_release"
    source_name = "Google (SerpAPI)"

    def collect(self, ctx: CollectionContext, company: dict, *, num: int = 10) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        if not settings.serpapi_api_key:
            return api_key_missing_result(self)

        query = build_press_query(company, conn=conn)
        params = {"engine": "google", "q": query, "api_key": settings.serpapi_api_key, "num": num}
        resp = get(SERPAPI, params=params)
        _save_raw(ctx, ticker=ticker, collector=self, url=SERPAPI, params=params, resp=resp)
        results = resp.json().get("organic_results", []) or []

        repo.delete_evidence(conn, ticker, self.name)
        rows = parse_press_rows(
            self, company, query, results, retrieval_date=collection_date_iso()
        )
        inserted = repo.insert_evidence(conn, rows)
        if not results:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="no organic results from SerpAPI",
                api_calls=1,
            )
        if inserted:
            return collector_result(
                CollectionStatus.SUCCESS,
                evidence_count=inserted,
                api_calls=1,
                source_hits=len(results),
                candidates_after_filter=inserted,
            )
        return collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
            message="organic results present; none matched AI press filter",
            api_calls=1,
            source_hits=len(results),
            candidates_after_filter=0,
        )
