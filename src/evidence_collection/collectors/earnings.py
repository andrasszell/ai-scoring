from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from ..config import settings
from ..dates import transcript_source_date
from ..db import repository as repo
from ..extraction import candidate_paragraphs, content_hash
from ..http import get
from ..models import CollectionContext, CollectorResult, collector_result
from ..outcomes import OutcomeReason
from ..status import CollectionStatus
from .base import Collector
from ..registry_gate import api_key_missing_result

BASE = "https://financialmodelingprep.com/api/v3"
LOOKBACK_YEARS = 6
logger = logging.getLogger(__name__)


class EarningsCallCollector(Collector):
    """Earnings-call transcript evidence via Financial Modeling Prep (optional).

    Transcript coverage is usually licensed; this adapter is isolated so it can be
    swapped for AlphaSense, FactSet, Bloomberg, Quartr, etc.
    """

    name = "earnings_calls"
    platform_id = "fmp_transcripts"
    version = "1.0.0"
    source_type = "earnings_call_transcript"
    source_name = "Financial Modeling Prep"

    def collect(self, ctx: CollectionContext, company: dict, *, limit_quarters: int = 4) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        if not settings.fmp_api_key:
            return api_key_missing_result(self)

        url = f"{BASE}/earning_call_transcript"
        repo.delete_evidence(conn, ticker, self.name)
        current_year = date.today().year
        transcripts_seen = 0
        api_calls = 0
        rows: list[dict] = []
        for year in range(current_year, current_year - LOOKBACK_YEARS, -1):
            for quarter in range(4, 0, -1):
                if transcripts_seen >= limit_quarters:
                    break
                params = {"symbol": ticker, "quarter": quarter, "year": year, "apikey": settings.fmp_api_key}
                try:
                    resp = get(url, params=params)
                    api_calls += 1
                    data = resp.json()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "FMP transcript fetch failed %s %s Q%s: %s", ticker, year, quarter, exc
                    )
                    continue
                if not data:
                    continue
                item = data[0] if isinstance(data, list) else data
                content = item.get("content") or item.get("transcript") or ""
                if not str(content).strip():
                    continue
                transcript_date, date_provenance = transcript_source_date(item, year=year, quarter=quarter)
                source_url = f"fmp://earning_call_transcript/{ticker}/{year}/Q{quarter}"
                transcripts_seen += 1
                # Persist raw transcript text so evidence can be reprocessed offline.
                text_dir = Path(settings.raw_dir) / "earnings" / ticker
                text_dir.mkdir(parents=True, exist_ok=True)
                text_path = text_dir / f"{year}Q{quarter}.txt"
                text_path.write_text(content, encoding="utf-8")
                document_id = repo.insert_document(
                    conn,
                    {
                        "company_id": company.get("company_id") or ticker,
                        "ticker": ticker,
                        "source_type": self.source_type,
                        "source_name": f"{year} Q{quarter}",
                        "source_url": source_url,
                        "source_date": transcript_date,
                        "title": f"{ticker} earnings call {year} Q{quarter}",
                        "text_path": str(text_path),
                        "content_hash": content_hash(content),
                        "parser_version": "fmp_transcript/1.0",
                        "metadata_json": json.dumps(
                            {"year": year, "quarter": quarter, "date_provenance": date_provenance}
                        ),
                    },
                )
                for p in candidate_paragraphs(content, settings.max_candidate_paragraphs // 2):
                    rows.append(
                        self.make_evidence(
                            company,
                            evidence_text=p["text"],
                            source_url=source_url,
                            source_date=transcript_date,
                            source_name=f"{year} Q{quarter}",
                            raw_document_id=document_id,
                            metadata={
                                "keywords": p["keywords"],
                                "year": year,
                                "quarter": quarter,
                                "date_provenance": date_provenance,
                            },
                        )
                    )
            if transcripts_seen >= limit_quarters:
                break

        inserted = repo.insert_evidence(conn, rows)
        if transcripts_seen == 0:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="no transcripts in lookback window",
                api_calls=api_calls,
            )
        if inserted:
            return collector_result(
                CollectionStatus.SUCCESS,
                evidence_count=inserted,
                documents_count=transcripts_seen,
                api_calls=api_calls,
                source_hits=transcripts_seen,
                candidates_after_filter=inserted,
            )
        return collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
            message="transcripts stored; no AI keyword paragraphs",
            documents_count=transcripts_seen,
            api_calls=api_calls,
            source_hits=transcripts_seen,
            candidates_after_filter=0,
        )
