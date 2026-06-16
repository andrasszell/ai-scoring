from __future__ import annotations

import json
import re
import time
from urllib.parse import urlparse

from ..config import settings
from ..registry_gate import api_key_missing_result
from ..db import repository as repo
from ..extraction import content_hash
from ..http import get
from ..models import CollectionContext, CollectorResult
from ..status import CollectionStatus
from ..universe.entity import search_name
from .base import Collector

SERPAPI = "https://serpapi.com/search.json"
AI_TERMS = '"AI" OR "artificial intelligence" OR "machine learning" OR "generative AI"'

# Keep this short: the Google Jobs engine returns nothing for long OR chains.
JOBS_QUERY_ROLES = '"artificial intelligence" OR "machine learning" OR "data scientist"'


def _save_raw(ctx, *, ticker, collector, url, params, resp) -> None:
    text = resp.text if resp is not None else ""
    repo.save_raw_response(
        ctx.conn,
        ticker=ticker,
        source_type=collector.source_type,
        collector_name=collector.name,
        collector_version=collector.version,
        request_url=url,
        request_params=json.dumps({k: v for k, v in (params or {}).items() if k != "api_key"}),
        status_code=getattr(resp, "status_code", None),
        response_text=text[:200_000],
        content_hash=content_hash(text),
    )


def _job_source(job: dict) -> str:
    """Best-effort apply/listing URL for a Google Jobs result."""
    for option in job.get("apply_options") or []:
        if option.get("link"):
            return option["link"]
    return job.get("share_link") or ""


def parse_job_rows(collector, company: dict, query: str, jobs_results: list[dict]) -> tuple[list[dict], int]:
    """Turn SerpAPI google_jobs results into evidence rows.

    Pure (no I/O) so it can be unit-tested with a sample payload. Returns the rows
    plus how many postings came via LinkedIn.
    """
    rows: list[dict] = []
    linkedin = 0
    for job in jobs_results:
        via = job.get("via", "") or ""
        platform = via.replace("via ", "").strip()
        is_linkedin = "linkedin" in via.lower()
        if is_linkedin:
            linkedin += 1
        text = " — ".join(
            x for x in [job.get("title"), job.get("company_name"), job.get("location"), via] if x
        )
        rows.append(
            collector.make_evidence(
                company,
                evidence_text=text,
                source_url=_job_source(job),
                evidence_title=job.get("title"),
                source_name=platform or "Google Jobs",
                metadata={"query": query, "platform": platform, "is_linkedin": is_linkedin},
            )
        )
    return rows, linkedin


class ProductServiceCollector(Collector):
    name = "web_products"
    platform_id = "serpapi_web"
    version = "1.0.0"
    source_type = "web_search_product"
    source_name = "Google (SerpAPI)"

    def collect(self, ctx: CollectionContext, company: dict, *, num: int = 10) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        if not settings.serpapi_api_key:
            return api_key_missing_result(self)
        query = f'"{search_name(company, conn=conn)}" ({AI_TERMS}) product OR platform OR solution OR service'
        params = {"engine": "google", "q": query, "api_key": settings.serpapi_api_key, "num": num}
        resp = get(SERPAPI, params=params)
        _save_raw(ctx, ticker=ticker, collector=self, url=SERPAPI, params=params, resp=resp)
        results = resp.json().get("organic_results", [])

        repo.delete_evidence(conn, ticker, self.name)
        rows = []
        for r in results:
            text = " — ".join(x for x in [r.get("title"), r.get("snippet")] if x)
            if not re.search(r"AI|artificial intelligence|machine learning|generative", text, re.I):
                continue
            rows.append(
                self.make_evidence(
                    company,
                    evidence_text=text,
                    source_url=r.get("link"),
                    evidence_title=r.get("title"),
                    metadata={"query": query, "domain": urlparse(r.get("link", "")).netloc},
                )
            )
        inserted = repo.insert_evidence(conn, rows)
        status = CollectionStatus.SUCCESS if inserted else CollectionStatus.NO_RESULTS
        return CollectorResult(status, evidence_count=inserted, api_calls=1)


class HiringCollector(Collector):
    name = "hiring_jobs"
    platform_id = "serpapi_jobs"
    version = "1.0.0"
    source_type = "job_posting"
    source_name = "Google Jobs (SerpAPI)"

    def _fetch_jobs(self, ctx, ticker, query: str, *, attempts: int = 3, pause: float = 1.5):
        """Query the Google Jobs engine, retrying on intermittent empty results."""
        api_calls = 0
        for attempt in range(attempts):
            params = {"engine": "google_jobs", "q": query, "api_key": settings.serpapi_api_key}
            resp = get(SERPAPI, params=params)
            api_calls += 1
            _save_raw(ctx, ticker=ticker, collector=self, url=SERPAPI, params=params, resp=resp)
            jobs = resp.json().get("jobs_results", []) or []
            if jobs or attempt == attempts - 1:
                return jobs, api_calls
            time.sleep(pause)
        return [], api_calls

    def collect(self, ctx: CollectionContext, company: dict) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        if not settings.serpapi_api_key:
            return api_key_missing_result(self)
        query = f"{search_name(company, conn=conn)} ({JOBS_QUERY_ROLES})"
        jobs_results, api_calls = self._fetch_jobs(ctx, ticker, query)

        rows, linkedin = parse_job_rows(self, company, query, jobs_results)
        repo.delete_evidence(conn, ticker, self.name)
        inserted = repo.insert_evidence(conn, rows)
        if inserted:
            repo.upsert_collection_metric(
                conn, run_id=ctx.run_id, ticker=ticker,
                name="hiring_linkedin_postings", value=float(linkedin), source=self.name,
            )
        status = CollectionStatus.SUCCESS if inserted else CollectionStatus.NO_RESULTS
        return CollectorResult(status, evidence_count=inserted, api_calls=api_calls)
