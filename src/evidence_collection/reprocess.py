from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .collectors import DOCUMENT_SOURCES, REGISTRY
from .config import settings
from .db import repository as repo
from .extraction import candidate_paragraphs
from .logging_config import get_logger

logger = get_logger("evidence_collection.reprocess")


def reprocess_documents(conn, sources: list[str] | None = None,
                        tickers: list[str] | None = None) -> dict:
    """Re-extract evidence from stored document text — no network calls.

    Makes reproducibility real (Coding Standards §1): if extraction logic improves,
    we can regenerate the evidence corpus from preserved raw documents instead of
    re-fetching from unstable source APIs.
    """
    selected = sources or list(DOCUMENT_SOURCES)
    norm_tickers = {t.upper().replace(".", "-") for t in tickers} if tickers else None
    totals = {"documents": 0, "evidence": 0, "skipped_missing_text": 0}

    for key in selected:
        source_type = DOCUMENT_SOURCES[key]
        collector = REGISTRY[key]
        rows = conn.execute(
            "SELECT * FROM documents WHERE source_type=? AND text_path IS NOT NULL ORDER BY ticker",
            (source_type,),
        ).fetchall()

        by_ticker: dict[str, list] = defaultdict(list)
        for d in rows:
            if norm_tickers and d["ticker"] not in norm_tickers:
                continue
            by_ticker[d["ticker"]].append(d)

        for ticker, docs in by_ticker.items():
            company_rows = repo.get_companies(conn, [ticker])
            company = company_rows[0] if company_rows else {"ticker": ticker, "company_name": ticker}
            repo.delete_evidence(conn, ticker, collector.name)
            evidence_rows = []
            for d in docs:
                path = Path(d["text_path"])
                if not path.exists():
                    totals["skipped_missing_text"] += 1
                    logger.warning("missing text_path for %s: %s", ticker, path)
                    continue
                text = path.read_text(encoding="utf-8")
                totals["documents"] += 1
                for p in candidate_paragraphs(text, settings.max_candidate_paragraphs):
                    evidence_rows.append(
                        collector.make_evidence(
                            company,
                            evidence_text=p["text"],
                            source_url=d["source_url"],
                            source_date=d["source_date"],
                            source_name=d["source_name"],
                            raw_document_id=d["id"],
                            metadata={"keywords": p["keywords"], "reprocessed": True},
                        )
                    )
            totals["evidence"] += repo.insert_evidence(conn, evidence_rows)

    return totals
