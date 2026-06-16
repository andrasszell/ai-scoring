from __future__ import annotations

import json

from ..dates import normalize_patent_date
from ..config import settings
from ..db import repository as repo
from ..extraction import content_hash
from ..http import get
from ..models import CollectionContext, CollectorResult, collector_result
from ..outcomes import OutcomeReason
from ..status import CollectionStatus
from ..universe.entity import clean_company_name
from .base import Collector
from ..registry_gate import api_key_missing_result

PATENTSVIEW = "https://search.patentsview.org/api/v1/patent/"


class PatentsCollector(Collector):
    """Approximate AI patent activity via PatentsView (optional, needs API key).

    Rough signal only: legal names and subsidiaries need cleanup for production.
    """

    name = "patents"
    platform_id = "patentsview"
    version = "1.0.0"
    source_type = "patent"
    source_name = "PatentsView"

    def collect(self, ctx: CollectionContext, company: dict) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        if not settings.patentsview_api_key:
            return api_key_missing_result(self)

        name = clean_company_name(company.get("company_name", ""))
        query = {
            "_and": [
                {"_text_any": {"patent_title": "artificial intelligence machine learning neural network"}},
                {"_text_any": {"assignees.assignee_organization": name}},
            ]
        }
        fields = ["patent_id", "patent_title", "patent_date", "assignees.assignee_organization"]
        params = {"q": json.dumps(query), "f": json.dumps(fields), "o": json.dumps({"per_page": 25})}
        headers = {"X-Api-Key": settings.patentsview_api_key}
        try:
            resp = get(PATENTSVIEW, params=params, headers=headers)
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            return CollectorResult(CollectionStatus.SOURCE_UNAVAILABLE, message=f"error: {exc}")

        repo.save_raw_response(
            conn, ticker=ticker, source_type=self.source_type, collector_name=self.name,
            collector_version=self.version, request_url=PATENTSVIEW, request_params=params["q"],
            status_code=getattr(resp, "status_code", None), response_text=resp.text[:200_000],
            content_hash=content_hash(resp.text),
        )

        patents = data.get("patents", []) or []
        total_hits = data.get("total_hits")
        if total_hits is None:
            total_hits = data.get("count", len(patents))

        repo.delete_evidence(conn, ticker, self.name)
        rows = []
        for p in patents[:25]:
            source_date, date_provenance = normalize_patent_date(p.get("patent_date"))
            rows.append(
                self.make_evidence(
                    company,
                    evidence_text=p.get("patent_title", ""),
                    source_url=f"https://patents.google.com/patent/US{p.get('patent_id')}",
                    source_date=source_date,
                    evidence_title=p.get("patent_title"),
                    metadata={
                        "patent_id": p.get("patent_id"),
                        "assignees": p.get("assignees"),
                        "total_hits": total_hits,
                        "date_provenance": date_provenance,
                    },
                )
            )
        inserted = repo.insert_evidence(conn, rows)
        repo.upsert_collection_metric(
            conn, run_id=ctx.run_id, ticker=ticker,
            name="patent_total_hits", value=float(total_hits), source=self.name,
        )
        hits = int(total_hits or 0)
        if hits == 0:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="PatentsView total_hits is zero",
                api_calls=1,
            )
        if inserted:
            return collector_result(
                CollectionStatus.SUCCESS,
                evidence_count=inserted,
                api_calls=1,
                source_hits=hits,
                candidates_after_filter=inserted,
            )
        return collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
            message="patent hits returned but none inserted",
            api_calls=1,
            source_hits=hits,
            candidates_after_filter=0,
        )
