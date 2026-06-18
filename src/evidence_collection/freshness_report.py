from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .db import repository as repo
from .freshness import load_freshness_config, parse_status_timestamp

FRESH_STATUSES = frozenset({"success", "no_results", "skipped"})


def _days_since(dt: datetime | None, now: datetime) -> int | None:
    if dt is None:
        return None
    return max(0, (now - dt).days)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _evidence_summary(conn: sqlite3.Connection, tickers: list[str] | None) -> dict[str, dict]:
    sql = """
        SELECT ticker,
               COUNT(*) AS evidence_count,
               MIN(created_at) AS oldest_evidence_at,
               MAX(created_at) AS newest_evidence_at
        FROM evidence_items
    """
    params: list = []
    if tickers:
        norm = [t.upper().replace(".", "-") for t in tickers]
        sql += f" WHERE ticker IN ({','.join('?' for _ in norm)})"
        params = norm
    sql += " GROUP BY ticker"
    return {row["ticker"]: dict(row) for row in conn.execute(sql, params).fetchall()}


def _evidence_by_source(
    conn: sqlite3.Connection,
    tickers: list[str] | None,
) -> dict[tuple[str, str], dict]:
    sql = """
        SELECT ticker, source_type,
               COUNT(*) AS evidence_count,
               MIN(created_at) AS oldest_evidence_at,
               MAX(created_at) AS newest_evidence_at
        FROM evidence_items
    """
    params: list = []
    if tickers:
        norm = [t.upper().replace(".", "-") for t in tickers]
        sql += f" WHERE ticker IN ({','.join('?' for _ in norm)})"
        params = norm
    sql += " GROUP BY ticker, source_type"
    out: dict[tuple[str, str], dict] = {}
    for row in conn.execute(sql, params).fetchall():
        out[(row["ticker"], row["source_type"])] = dict(row)
    return out


def build_freshness_report(
    conn: sqlite3.Connection,
    companies: list[dict],
    *,
    stale_days: int | None = None,
    now: datetime | None = None,
) -> dict:
    """Build corpus freshness report for dashboard / cron use."""
    current = now or datetime.now(timezone.utc)
    default_days, sla_by_source = load_freshness_config()
    threshold = stale_days if stale_days is not None else default_days
    tickers = [c["ticker"] for c in companies]
    evidence_by_ticker = _evidence_summary(conn, tickers or None)
    evidence_by_source = _evidence_by_source(conn, tickers or None)
    statuses = repo.status_summary(conn, tickers or None)
    status_by_pair = {(r["ticker"], r["source_type"]): r for r in statuses}

    company_rows: list[dict] = []
    stale_company_count = 0
    stale_source_count = 0
    never_collected_count = 0

    for company in sorted(companies, key=lambda c: c["ticker"]):
        ticker = company["ticker"]
        ev = evidence_by_ticker.get(ticker, {})
        evidence_count = int(ev.get("evidence_count") or 0)
        oldest_raw = ev.get("oldest_evidence_at")
        newest_raw = ev.get("newest_evidence_at")
        oldest_dt = parse_status_timestamp(oldest_raw)
        newest_dt = parse_status_timestamp(newest_raw)
        days_since_newest = _days_since(newest_dt, current)

        company_stale = evidence_count == 0 or (
            days_since_newest is not None and days_since_newest > threshold
        )
        if company_stale:
            stale_company_count += 1
        company_stale_reason = None
        if evidence_count == 0:
            company_stale_reason = "no_evidence"
        elif company_stale:
            company_stale_reason = "past_threshold"

        sources: list[dict] = []
        seen_sources = {st for (t, st) in status_by_pair if t == ticker}
        seen_sources |= {st for (t, st) in evidence_by_source if t == ticker}

        for source_type in sorted(seen_sources):
            status_row = status_by_pair.get((ticker, source_type))
            ev_row = evidence_by_source.get((ticker, source_type), {})
            sla_days = sla_by_source.get(source_type, default_days)
            last_status = status_row.get("status") if status_row else None
            last_collected = parse_status_timestamp(
                status_row.get("created_at") if status_row else None
            )
            days_since_collection = _days_since(last_collected, current)
            source_evidence_count = int(ev_row.get("evidence_count") or 0)

            stale_reason = None
            is_stale = False
            if status_row is None:
                stale_reason = "never_collected"
                is_stale = True
                never_collected_count += 1
            elif last_status not in FRESH_STATUSES:
                stale_reason = "last_failed"
                is_stale = True
            elif days_since_collection is not None and days_since_collection > sla_days:
                stale_reason = "past_sla"
                is_stale = True
            if is_stale:
                stale_source_count += 1

            sources.append(
                {
                    "source_type": source_type,
                    "collector_name": status_row.get("collector_name") if status_row else None,
                    "last_status": last_status,
                    "last_collected_at": _iso(last_collected),
                    "days_since_collection": days_since_collection,
                    "sla_days": sla_days,
                    "is_stale": is_stale,
                    "stale_reason": stale_reason,
                    "evidence_count": source_evidence_count,
                    "oldest_evidence_at": ev_row.get("oldest_evidence_at"),
                    "newest_evidence_at": ev_row.get("newest_evidence_at"),
                }
            )

        company_rows.append(
            {
                "ticker": ticker,
                "company_name": company.get("company_name"),
                "evidence_count": evidence_count,
                "oldest_evidence_at": oldest_raw,
                "newest_evidence_at": newest_raw,
                "days_since_newest_evidence": days_since_newest,
                "is_stale": company_stale,
                "stale_reason": company_stale_reason,
                "stale_threshold_days": threshold,
                "sources": sources,
            }
        )

    with_evidence = sum(1 for row in company_rows if row["evidence_count"] > 0)
    return {
        "generated_at": _iso(current),
        "stale_threshold_days": threshold,
        "sla_by_source_type": sla_by_source,
        "summary": {
            "companies_total": len(company_rows),
            "companies_with_evidence": with_evidence,
            "stale_companies": stale_company_count,
            "stale_sources": stale_source_count,
            "sources_never_collected": never_collected_count,
        },
        "companies": company_rows,
    }


def format_freshness_report(report: dict, *, stale_only: bool = False) -> str:
    summary = report["summary"]
    threshold = report["stale_threshold_days"]
    lines = [
        f"Freshness report ({report['generated_at']}, stale threshold: {threshold} days)",
        f"  Companies: {summary['companies_total']} total, "
        f"{summary['companies_with_evidence']} with evidence, "
        f"{summary['stale_companies']} stale (no evidence in {threshold}d)",
        f"  Sources: {summary['stale_sources']} past SLA / failed / never collected, "
        f"{summary['sources_never_collected']} never collected",
        "",
    ]

    all_companies = report["companies"]
    stale_companies = [c for c in all_companies if c["is_stale"]]

    if not stale_only or stale_companies:
        if stale_companies:
            lines.append(f"Stale companies (no evidence in {threshold} days):")
            lines.append(f"  {'TICKER':<8} {'EVID':>6} {'NEWEST':<20} {'DAYS':>5} {'REASON':<14}")
            for row in stale_companies:
                newest = (row.get("newest_evidence_at") or "-")[:19]
                days = row.get("days_since_newest_evidence")
                days_s = str(days) if days is not None else "-"
                lines.append(
                    f"  {row['ticker']:<8} {row['evidence_count']:>6} {newest:<20} "
                    f"{days_s:>5} {row.get('stale_reason') or '':<14}"
                )
            lines.append("")

    source_rows: list[dict] = []
    for company in all_companies:
        for source in company.get("sources") or []:
            if stale_only and not source.get("is_stale"):
                continue
            source_rows.append({"ticker": company["ticker"], **source})

    if source_rows:
        lines.append("Per-source collection (SLA from config/source_freshness_ttl.yaml):")
        lines.append(
            f"  {'TICKER':<8} {'SOURCE':<24} {'STATUS':<18} {'LAST':<20} "
            f"{'DAYS':>5} {'SLA':>4} {'STALE':<12}"
        )
        for row in source_rows:
            last = (row.get("last_collected_at") or "-")[:19]
            days = row.get("days_since_collection")
            days_s = str(days) if days is not None else "-"
            stale = row.get("stale_reason") or ("no" if not row.get("is_stale") else "yes")
            lines.append(
                f"  {row['ticker']:<8} {row['source_type']:<24} "
                f"{(row.get('last_status') or '-'):<18} {last:<20} "
                f"{days_s:>5} {row.get('sla_days', '-'):>4} {stale:<12}"
            )
    elif stale_only:
        lines.append("No stale companies or sources in scope.")

    return "\n".join(lines)


def write_freshness_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
