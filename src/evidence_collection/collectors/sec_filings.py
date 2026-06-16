from __future__ import annotations

import json
from pathlib import Path

from ..config import settings
from ..db import repository as repo
from ..extraction import candidate_paragraphs, content_hash, html_to_text
from ..http import get
from ..models import CollectionContext, CollectorResult
from ..status import CollectionStatus
from .base import Collector

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_no_dashes}/{primary_doc}"

# Domestic 10-K plus amendments and the foreign-filer equivalents (20-F, 40-F).
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")

PARSER_VERSION = "html_to_text/1.0"


def _latest_annual_filing(submissions: dict) -> dict | None:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])
    for form, acc, doc, date in zip(forms, accession_numbers, primary_docs, filing_dates):
        if form in ANNUAL_FORMS:
            return {"form": form, "accession": acc, "primary_doc": doc, "filing_date": date}
    return None


class SecFilingsCollector(Collector):
    name = "sec_filings"
    version = "1.0.0"
    source_type = "sec_annual_filing"
    source_name = "SEC EDGAR"

    def collect(self, ctx: CollectionContext, company: dict) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        cik = company.get("cik")
        if not cik:
            return CollectorResult(CollectionStatus.COMPANY_NOT_FOUND, message="missing_cik")

        api_calls = 0
        submissions = get(SUBMISSIONS_URL.format(cik=cik), sec=True).json()
        api_calls += 1
        filing = _latest_annual_filing(submissions)
        if not filing:
            return CollectorResult(CollectionStatus.NO_RESULTS, api_calls=api_calls, message="no_annual_filing")

        cik_no_zeros = str(int(cik))
        url = ARCHIVES_URL.format(
            cik_no_zeros=cik_no_zeros,
            accession_no_dashes=filing["accession"].replace("-", ""),
            primary_doc=filing["primary_doc"],
        )
        raw = get(url, sec=True).text
        api_calls += 1
        text = html_to_text(raw)

        raw_dir = Path(settings.raw_dir) / "sec_filings" / ticker
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{filing['filing_date']}_{filing['primary_doc']}.html"
        text_path = raw_dir / f"{filing['filing_date']}_{filing['primary_doc']}.txt"
        raw_path.write_text(raw, encoding="utf-8")
        text_path.write_text(text, encoding="utf-8")

        document_id = repo.insert_document(
            conn,
            {
                "company_id": company.get("company_id") or ticker,
                "ticker": ticker,
                "source_type": self.source_type,
                "source_name": filing["form"],
                "source_url": url,
                "source_date": filing["filing_date"],
                "title": f"{ticker} {filing['form']} {filing['filing_date']}",
                "raw_path": str(raw_path),
                "text_path": str(text_path),
                "content_hash": content_hash(raw),
                "parser_version": PARSER_VERSION,
                "metadata_json": json.dumps({"form": filing["form"], "accession": filing["accession"]}),
            },
        )

        repo.delete_evidence(conn, ticker, self.name)
        rows = []
        for p in candidate_paragraphs(text, settings.max_candidate_paragraphs):
            rows.append(
                self.make_evidence(
                    company,
                    evidence_text=p["text"],
                    source_url=url,
                    source_date=filing["filing_date"],
                    source_name=filing["form"],
                    raw_document_id=document_id,
                    metadata={"keywords": p["keywords"], "form": filing["form"]},
                )
            )
        inserted = repo.insert_evidence(conn, rows)
        status = CollectionStatus.SUCCESS if inserted else CollectionStatus.NO_RESULTS
        return CollectorResult(status, evidence_count=inserted, documents_count=1, api_calls=api_calls)
