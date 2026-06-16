from __future__ import annotations

import argparse
from pathlib import Path

from .collectors import SOURCE_KEYS, get_collectors
from .config import DEFAULT_TICKERS, settings
from .db import apply_migrations, connect, current_version
from .db import repository as repo
from .exporters import export_evidence_jsonl, export_table_csv
from .logging_config import get_logger, setup_logging
from .reprocess import reprocess_documents
from .registry_gate import get_platform_registry, reset_registry_cache
from .platforms import Platform, runtime_key_status
from .runner import run_collection
from .universe import (
    enrich_companies,
    fetch_sec_companies,
    load_universe,
    match_rows,
    resolve_company,
)

logger = get_logger("evidence_collection.cli")


def _conn():
    conn = connect(settings.db_path)
    apply_migrations(conn)
    return conn


def _normalize(tickers: list[str] | None) -> list[str] | None:
    if not tickers:
        return None
    return [t.upper().replace(".", "-") for t in tickers]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_init_db(args) -> None:
    conn = _conn()
    version = current_version(conn)
    conn.close()
    print(f"Initialized database: {settings.db_path} (schema version {version})")


def cmd_load_companies(args) -> None:
    conn = _conn()
    n, aliases = load_universe(conn, limit=args.limit)
    conn.close()
    print(f"Loaded {n} companies into {settings.db_path} ({aliases} aliases from config)")


def _select_companies(conn, args) -> tuple[list[dict], list[str] | None]:
    """Resolve the company set for a collect run. Returns (companies, requested)."""
    if getattr(args, "all", False):
        return repo.get_companies(conn), None
    if getattr(args, "ticker", None):
        requested = _normalize(args.ticker)
        return repo.get_companies(conn, requested), requested
    if getattr(args, "limit", None):
        return repo.get_companies(conn, limit=args.limit), None
    requested = list(DEFAULT_TICKERS)
    print(f"No --ticker/--limit/--all given; collecting the default top "
          f"{len(requested)} companies: {', '.join(requested)}")
    return repo.get_companies(conn, requested), requested


def cmd_collect(args) -> None:
    conn = _conn()
    if repo.count_companies(conn) == 0:
        print("Company universe is empty; loading S&P 500 first...")
        load_universe(conn)

    companies, requested = _select_companies(conn, args)
    if requested:
        found = {c["ticker"] for c in companies}
        missing = sorted(set(requested) - found)
        if missing:
            print(f"Not in database (skipped): {', '.join(missing)}. "
                  "Run `ai-collect load-companies` to load the full universe.")
    if not companies:
        conn.close()
        raise SystemExit("No matching companies found. Run: ai-collect load-companies")

    companies = enrich_companies(conn, companies)
    collectors = get_collectors(args.source)
    totals = run_collection(
        conn, companies, collectors,
        command="collect",
        args={"tickers": requested, "all": args.all, "sources": args.source or SOURCE_KEYS},
    )
    conn.close()
    print(f"\nRun #{totals['run_id']}: {totals['evidence']} evidence items, "
          f"{totals['documents']} documents, {totals['ok']} ok / {totals['failed']} failed "
          f"in {totals['runtime_seconds']}s")


def cmd_analyze(args) -> None:
    conn = _conn()
    if repo.count_companies(conn) == 0:
        print("Company universe is empty; loading S&P 500 first...")
        load_universe(conn)

    query = " ".join(args.name).strip()
    matches = resolve_company(conn, query)
    if not matches:
        print(f"'{query}' is not in the loaded S&P 500 universe; searching all SEC filers...")
        matches = match_rows(fetch_sec_companies(), query)
    if not matches:
        conn.close()
        raise SystemExit(f"No company matches '{query}'. Try the exact ticker symbol.")
    if len(matches) > 1:
        listing = "\n".join(f"  - {m['ticker']}: {m['company_name']}" for m in matches[:15])
        extra = "" if len(matches) <= 15 else f"\n  ...and {len(matches) - 15} more"
        conn.close()
        raise SystemExit(f"'{query}' matches multiple companies:\n{listing}{extra}\n"
                         "Re-run with a more specific name or the exact ticker.")

    company = enrich_companies(conn, [matches[0]])[0]
    repo.upsert_companies(conn, [company])
    print(f"Analyzing {company['ticker']} — {company['company_name']} "
          f"({company.get('sector') or 'n/a'})")
    totals = run_collection(
        conn, [company], get_collectors(args.source),
        command="analyze",
        args={"query": query, "ticker": company["ticker"], "sources": args.source or SOURCE_KEYS},
    )
    conn.close()
    print(f"\nCollected {totals['evidence']} evidence items, {totals['documents']} documents "
          f"({totals['ok']} ok / {totals['failed']} failed).")


def cmd_export_evidence(args) -> None:
    conn = _conn()
    tickers = _normalize(args.ticker)
    if args.format == "jsonl":
        n = export_evidence_jsonl(conn, args.output, tickers)
    else:
        n = export_table_csv(conn, "evidence_items", args.output, tickers)
    conn.close()
    print(f"Wrote {n} evidence rows to {args.output}")


def cmd_export_documents(args) -> None:
    conn = _conn()
    n = export_table_csv(conn, "documents", args.output, _normalize(args.ticker))
    conn.close()
    print(f"Wrote {n} document rows to {args.output}")


def cmd_export_companies(args) -> None:
    conn = _conn()
    n = export_table_csv(conn, "companies", args.output, _normalize(args.ticker))
    conn.close()
    print(f"Wrote {n} company rows to {args.output}")


def cmd_export_all(args) -> None:
    conn = _conn()
    out = Path(args.output_dir)
    tickers = _normalize(args.ticker)
    counts = {
        "companies.csv": export_table_csv(conn, "companies", out / "companies.csv", tickers),
        "documents.csv": export_table_csv(conn, "documents", out / "documents.csv", tickers),
        "evidence_items.csv": export_table_csv(conn, "evidence_items", out / "evidence_items.csv", tickers),
        "collector_status.csv": export_table_csv(conn, "collector_status", out / "collector_status.csv", tickers),
        "evidence_items.jsonl": export_evidence_jsonl(conn, out / "evidence_items.jsonl", tickers),
    }
    conn.close()
    for name, n in counts.items():
        print(f"  {n:>6}  {out / name}")


def cmd_reprocess(args) -> None:
    conn = _conn()
    totals = reprocess_documents(conn, sources=args.source, tickers=_normalize(args.ticker))
    conn.close()
    print(f"Reprocessed {totals['documents']} documents -> {totals['evidence']} evidence items"
          + (f" ({totals['skipped_missing_text']} skipped: missing text)"
             if totals['skipped_missing_text'] else ""))


def cmd_validate(args) -> None:
    conn = _conn()
    report = repo.quality_report(conn)
    conn.close()
    print(f"Evidence items: {report['total_evidence']} "
          f"across {report['companies_with_evidence']} companies\n")
    print("Validation (violations should be 0):")
    violations = report["violations"]
    for name, count in violations.items():
        flag = "OK " if count == 0 else "!! "
        print(f"  {flag}{name:<28} {count}")
    print("\nCoverage by source:")
    print(f"  {'SOURCE':<24} {'CATEGORY':<20} {'RELIABILITY':<12} {'ROWS':>6} {'COS':>5}")
    for c in report["coverage"]:
        print(f"  {c['source_type']:<24} {str(c['source_category']):<20} "
              f"{str(c['source_reliability']):<12} {c['rows']:>6} {c['companies']:>5}")
    if any(violations.values()):
        raise SystemExit(1)


def format_company_identity_report(conn, ticker: str) -> str:
    """Build a human-readable identity + status summary for one ticker."""
    companies = repo.get_companies(conn, [ticker])
    if not companies:
        raise ValueError(f"Ticker {ticker!r} not in database. Run: ai-collect load-companies")
    company = companies[0]
    aliases = repo.get_aliases(conn, ticker)
    statuses = repo.status_summary(conn, [ticker])

    lines = [
        f"{company['ticker']} — {company.get('company_name') or 'n/a'}",
        f"  CIK:             {company.get('cik') or 'n/a'}",
        f"  Sector:          {company.get('sector') or 'n/a'}",
        f"  Industry:        {company.get('industry') or 'n/a'}",
        f"  Website domain:  {company.get('website_domain') or 'n/a'}",
    ]
    if aliases:
        lines.append("  Aliases:")
        for row in aliases:
            lines.append(f"    - {row['alias']} ({row['alias_type']})")
    else:
        lines.append("  Aliases:         (none)")
    if statuses:
        lines.append("  Last collection status:")
        for row in statuses:
            msg = f" — {row['message']}" if row.get("message") else ""
            lines.append(
                f"    {row['source_type']:<24} {row['status']:<18} "
                f"evidence={row['evidence_count']}{msg}"
            )
    else:
        lines.append("  Last collection status: (none — run ai-collect collect)")
    return "\n".join(lines)


def cmd_validate_company(args) -> None:
    conn = _conn()
    ticker = _normalize([args.ticker])[0]
    try:
        print(format_company_identity_report(conn, ticker))
    except ValueError as exc:
        conn.close()
        raise SystemExit(str(exc)) from exc
    conn.close()


def cmd_status(args) -> None:
    conn = _conn()
    rows = repo.status_summary(conn, _normalize(args.ticker))
    conn.close()
    if not rows:
        print("No collection runs recorded yet. Run: ai-collect collect")
        return
    print(f"{'TICKER':<8} {'SOURCE':<22} {'STATUS':<18} {'EVID':>5} {'DOCS':>5}  MESSAGE")
    for r in rows:
        print(f"{r['ticker']:<8} {r['source_type']:<22} {r['status']:<18} "
              f"{r['evidence_count']:>5} {r['documents_count']:>5}  {r['message'] or ''}")


def format_platforms_table(platforms: list[Platform], *, registry_version: str) -> str:
    lines = [
        f"Platform registry v{registry_version} ({len(platforms)} platform(s))",
        "",
        f"{'ID':<20} {'COLLECTOR':<16} {'PHASE':>5} {'EN':>3} {'VENDOR':<26} "
        f"{'ENV_KEY':<24} {'KEY_STATUS':<12} {'COST':<6}",
    ]
    for platform in platforms:
        env_key = platform.auth.env_key or "-"
        enabled = "yes" if platform.enabled else "no"
        lines.append(
            f"{platform.id:<20} {platform.collector:<16} {platform.phase:>5} {enabled:>3} "
            f"{platform.vendor[:26]:<26} {env_key:<24} "
            f"{runtime_key_status(platform.auth):<12} {platform.cost_model:<6}"
        )
    return "\n".join(lines)


def cmd_show_platforms(args) -> None:
    registry = get_platform_registry()
    platforms = list(registry.platforms)
    phase = args.phase
    if phase is None and not args.all:
        phase = 1
    if phase is not None:
        platforms = [p for p in platforms if p.phase == phase]
    if not args.all:
        platforms = [p for p in platforms if p.enabled]
    print(format_platforms_table(platforms, registry_version=registry.registry_version))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _add_source_flag(s) -> None:
    s.add_argument(
        "--source",
        nargs="*",
        choices=SOURCE_KEYS,
        help=f"Limit to these sources (default: all). Choices: {', '.join(SOURCE_KEYS)}",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai-collect", description="Evidence Discovery Layer CLI.")
    p.add_argument("--log-level", default=settings.log_level, help="DEBUG, INFO, WARNING, ...")
    sub = p.add_subparsers(required=True, dest="command")

    s = sub.add_parser("init-db", help="Create the database and apply migrations.")
    s.set_defaults(func=cmd_init_db)

    s = sub.add_parser("load-companies", help="Load the company universe (S&P 500 + CIKs).")
    s.add_argument("--limit", type=int, default=None)
    s.set_defaults(func=cmd_load_companies)

    s = sub.add_parser("collect", help="Collect evidence for companies.")
    s.add_argument("--ticker", nargs="*", help="Tickers, e.g. MSFT NVDA. Default: top S&P 500.")
    s.add_argument("--limit", type=int, default=None, help="Collect first N loaded companies.")
    s.add_argument("--all", action="store_true", help="Collect every loaded company.")
    _add_source_flag(s)
    s.set_defaults(func=cmd_collect)

    s = sub.add_parser("analyze", help="Collect evidence for one company by name or ticker.")
    s.add_argument("name", nargs="+", help="Company name or ticker, e.g. Microsoft or MSFT")
    _add_source_flag(s)
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("export-evidence", help="Export evidence items (CSV or JSONL).")
    s.add_argument("--output", default="data/exports/evidence_items.csv")
    s.add_argument("--format", choices=["csv", "jsonl"], default="csv")
    s.add_argument("--ticker", nargs="*", help="Only export these tickers.")
    s.set_defaults(func=cmd_export_evidence)

    s = sub.add_parser("export-documents", help="Export the document manifest.")
    s.add_argument("--output", default="data/exports/documents.csv")
    s.add_argument("--ticker", nargs="*")
    s.set_defaults(func=cmd_export_documents)

    s = sub.add_parser("export-companies", help="Export the company universe.")
    s.add_argument("--output", default="data/exports/companies.csv")
    s.add_argument("--ticker", nargs="*")
    s.set_defaults(func=cmd_export_companies)

    s = sub.add_parser("export-all", help="Export the full corpus (companies, documents, evidence, status).")
    s.add_argument("--output-dir", default="data/exports")
    s.add_argument("--ticker", nargs="*")
    s.set_defaults(func=cmd_export_all)

    s = sub.add_parser("validate", help="Audit the evidence corpus for rule violations + coverage.")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("reprocess", help="Re-extract evidence from stored documents (no network).")
    s.add_argument("--source", nargs="*", choices=["sec", "earnings"],
                   help="Document sources to reprocess (default: all document sources).")
    s.add_argument("--ticker", nargs="*")
    s.set_defaults(func=cmd_reprocess)

    s = sub.add_parser("validate-company", help="Show identity + aliases + last status for one ticker.")
    s.add_argument("ticker", help="Ticker symbol, e.g. MSFT")
    s.set_defaults(func=cmd_validate_company)

    s = sub.add_parser("status", help="Show the latest collection status per company/source.")
    s.add_argument("--ticker", nargs="*")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("show-platforms", help="List platform registry entries and API key status.")
    s.add_argument("--phase", type=int, default=None, help="Filter by phase (default: 1, or all phases with --all).")
    s.add_argument("--all", action="store_true", help="Include disabled platforms (all phases unless --phase set).")
    s.set_defaults(func=cmd_show_platforms)
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(getattr(args, "log_level", "INFO"))
    args.func(args)


if __name__ == "__main__":
    main()
