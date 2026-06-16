from __future__ import annotations

from datetime import date

DATE_PROVENANCE_ORIGIN = "origin"
DATE_PROVENANCE_RETRIEVAL = "retrieval"
DATE_PROVENANCE_QUARTER_ANCHOR = "quarter_anchor"


def collection_date_iso() -> str:
    return date.today().isoformat()


def normalize_patent_date(value) -> tuple[str, str]:
    """Return ISO-ish patent date and provenance."""
    if value is None:
        return collection_date_iso(), DATE_PROVENANCE_RETRIEVAL
    text = str(value).strip()
    if not text:
        return collection_date_iso(), DATE_PROVENANCE_RETRIEVAL
    return text[:10], DATE_PROVENANCE_ORIGIN


def normalize_publication_year(year) -> tuple[str, str]:
    """Map Semantic Scholar year to a source_date anchor."""
    if year is None:
        return collection_date_iso(), DATE_PROVENANCE_RETRIEVAL
    text = str(year).strip()
    if not text:
        return collection_date_iso(), DATE_PROVENANCE_RETRIEVAL
    if len(text) == 4 and text.isdigit():
        return f"{text}-01-01", DATE_PROVENANCE_ORIGIN
    return text, DATE_PROVENANCE_ORIGIN


def normalize_github_datetime(value) -> tuple[str, str]:
    """Map GitHub pushed_at ISO timestamp to source_date."""
    if value is None:
        return collection_date_iso(), DATE_PROVENANCE_RETRIEVAL
    text = str(value).strip()
    if not text:
        return collection_date_iso(), DATE_PROVENANCE_RETRIEVAL
    return text[:10], DATE_PROVENANCE_ORIGIN


def job_posted_date(job: dict, *, fallback: str | None = None) -> tuple[str, str]:
    """Extract posting time from Google Jobs payload (relative text is acceptable)."""
    fb = fallback or collection_date_iso()
    for key in ("posted_at", "date"):
        value = job.get(key)
        if value and str(value).strip():
            return str(value).strip(), DATE_PROVENANCE_ORIGIN
    extensions = job.get("detected_extensions") or {}
    posted = extensions.get("posted_at")
    if posted and str(posted).strip():
        return str(posted).strip(), DATE_PROVENANCE_ORIGIN
    for item in job.get("extensions") or []:
        text = str(item).strip()
        if text.lower().endswith("ago") or "posted" in text.lower():
            return text, DATE_PROVENANCE_ORIGIN
    return fb, DATE_PROVENANCE_RETRIEVAL


def web_result_date(result: dict, *, fallback: str | None = None) -> tuple[str, str]:
    """Use organic-result date when SerpAPI exposes it; else retrieval date."""
    fb = fallback or collection_date_iso()
    value = result.get("date")
    if value and str(value).strip():
        return str(value).strip(), DATE_PROVENANCE_ORIGIN
    return fb, DATE_PROVENANCE_RETRIEVAL


def transcript_source_date(item: dict, *, year: int, quarter: int) -> tuple[str, str]:
    """Prefer FMP transcript date; fall back to calendar quarter anchor."""
    raw = item.get("date")
    if raw and str(raw).strip():
        return str(raw).strip()[:10], DATE_PROVENANCE_ORIGIN
    month = min(quarter * 3, 12)
    return f"{year}-{month:02d}-01", DATE_PROVENANCE_QUARTER_ANCHOR
