from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from ..config import settings
from ..dates import collection_date_iso, web_result_date
from ..db import repository as repo
from ..extraction import candidate_paragraphs, content_hash, html_to_text
from ..http import get
from ..models import CollectionContext, CollectorResult, collector_result
from ..outcomes import OutcomeReason
from ..registry_gate import api_key_missing_result
from ..status import CollectionStatus
from .base import Collector
from .serpapi import AI_TERMS, SERPAPI, _save_raw

DOC_TERMS = '(documentation OR "developer guide" OR "API reference" OR docs OR "product guide")'
PARSER_VERSION = "html_to_text/1.0"
MAX_SEARCH_RESULTS = 8
MAX_PAGES = 5
MIN_TEXT_CHARS = 200


def build_product_docs_query(company: dict) -> str | None:
    """Return a site-restricted documentation search query, or None without domain."""
    domain = (company.get("website_domain") or "").strip().lower().removeprefix("www.")
    if not domain:
        return None
    return f"site:{domain} ({AI_TERMS}) {DOC_TERMS}"


def url_on_company_domain(url: str | None, website_domain: str | None) -> bool:
    if not url or not website_domain:
        return False
    netloc = urlparse(url).netloc.lower().removeprefix("www.")
    domain = website_domain.lower().removeprefix("www.").strip()
    return bool(domain) and (netloc == domain or netloc.endswith("." + domain))


def select_doc_results(
    organic_results: list[dict],
    website_domain: str,
    *,
    limit: int = MAX_PAGES,
) -> list[dict]:
    """Keep first-party documentation URLs from SerpAPI organic results."""
    selected: list[dict] = []
    seen: set[str] = set()
    for result in organic_results:
        link = (result.get("link") or "").strip()
        if not link or link in seen:
            continue
        if not url_on_company_domain(link, website_domain):
            continue
        seen.add(link)
        selected.append(result)
        if len(selected) >= limit:
            break
    return selected


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/").replace("/", "_") or "index"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", path)[:80]
    return slug or "page"


class ProductDocsCollector(Collector):
    """First-party product and developer documentation via SerpAPI discovery + page fetch.

    Stores fetched pages for offline ``reprocess``. Requires ``website_domain`` on the
    company row (seeded from ``config/company_domains.yaml``).
    """

    name = "product_docs"
    platform_id = "product_documentation"
    version = "1.0.0"
    source_type = "product_documentation"
    source_name = "Company documentation"

    def collect(self, ctx: CollectionContext, company: dict) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        domain = (company.get("website_domain") or "").strip()
        if not settings.serpapi_api_key:
            return api_key_missing_result(self)
        query = build_product_docs_query(company)
        if not query:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="website_domain required for product documentation search",
            )

        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.serpapi_api_key,
            "num": MAX_SEARCH_RESULTS,
        }
        resp = get(SERPAPI, params=params)
        api_calls = 1
        _save_raw(ctx, ticker=ticker, collector=self, url=SERPAPI, params=params, resp=resp)
        organic = resp.json().get("organic_results", []) or []
        candidates = select_doc_results(organic, domain)

        repo.delete_evidence(conn, ticker, self.name)
        retrieval = collection_date_iso()
        rows: list[dict] = []
        documents_stored = 0
        fetch_failures = 0

        raw_dir = Path(settings.raw_dir) / "product_docs" / ticker
        raw_dir.mkdir(parents=True, exist_ok=True)

        for result in candidates:
            link = result.get("link")
            title = result.get("title") or link
            source_date, date_provenance = web_result_date(result, fallback=retrieval)
            try:
                page_resp = get(link)
                api_calls += 1
                raw_html = page_resp.text
            except Exception:  # noqa: BLE001
                fetch_failures += 1
                continue

            text = html_to_text(raw_html)
            if len(text) < MIN_TEXT_CHARS:
                continue

            slug = _slug_from_url(link)
            raw_path = raw_dir / f"{slug}.html"
            text_path = raw_dir / f"{slug}.txt"
            raw_path.write_text(raw_html, encoding="utf-8")
            text_path.write_text(text, encoding="utf-8")

            document_id = repo.insert_document(
                conn,
                {
                    "company_id": company.get("company_id") or ticker,
                    "ticker": ticker,
                    "source_type": self.source_type,
                    "source_name": self.source_name,
                    "source_url": link,
                    "source_date": source_date,
                    "title": title,
                    "raw_path": str(raw_path),
                    "text_path": str(text_path),
                    "content_hash": content_hash(raw_html),
                    "parser_version": PARSER_VERSION,
                    "metadata_json": json.dumps(
                        {"query": query, "date_provenance": date_provenance, "title": title}
                    ),
                },
            )
            documents_stored += 1
            for paragraph in candidate_paragraphs(text, settings.max_candidate_paragraphs // max(1, len(candidates))):
                rows.append(
                    self.make_evidence(
                        company,
                        evidence_text=paragraph["text"],
                        source_url=link,
                        source_date=source_date,
                        evidence_title=title,
                        raw_document_id=document_id,
                        metadata={"keywords": paragraph["keywords"], "query": query},
                    )
                )

        inserted = repo.insert_evidence(conn, rows)
        if not organic:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="no organic results from SerpAPI",
                api_calls=api_calls,
            )
        if not candidates:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
                message="search results present; none on company domain",
                api_calls=api_calls,
                source_hits=len(organic),
                candidates_after_filter=0,
            )
        if documents_stored == 0:
            status = CollectionStatus.SOURCE_UNAVAILABLE
            if fetch_failures == len(candidates):
                message = "documentation URLs found but all page fetches failed"
            else:
                message = "documentation pages too short or empty after fetch"
            return CollectorResult(status, message=message, api_calls=api_calls, source_hits=len(candidates))
        if inserted:
            return collector_result(
                CollectionStatus.SUCCESS,
                evidence_count=inserted,
                documents_count=documents_stored,
                api_calls=api_calls,
                source_hits=len(organic),
                candidates_after_filter=inserted,
            )
        return collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
            message="documentation stored; no AI keyword paragraphs",
            documents_count=documents_stored,
            api_calls=api_calls,
            source_hits=len(organic),
            candidates_after_filter=0,
        )
