from __future__ import annotations

import argparse
import json
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
from .outcomes import parse_outcome_detail, parse_outcome_reason
from .runner import run_collection
from .freshness import policy_from_collect_args
from .universe import (
    enrich_companies,
    ensure_pilot_companies,
    ensure_validation_companies,
    format_ambiguous_message,
    load_universe,
    lookup_company,
    materialize_company,
    upsert_tickers_from_sec,
    github_orgs_for_ticker,
)
from .universe.verify import DEFAULT_SPOT_CHECK, spot_check_tickers, universe_stats
from .costs import format_cost_report, summarize_run_costs
from .retry import build_retry_targets, format_retry_plan, retry_failed_collection
from .freshness_report import build_freshness_report, format_freshness_report, write_freshness_report

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
    if getattr(args, "validation_set", False):
        companies, tickers = ensure_validation_companies(conn)
        enrich_companies(conn, companies)
        print(f"Validation set: {len(tickers)} tickers ensured in database "
              f"({len(companies)} resolved).")
    if getattr(args, "pilot_set", False):
        companies, tickers = ensure_pilot_companies(conn)
        enrich_companies(conn, companies)
        print(f"Phase 3 pilot set: {len(tickers)} tickers ensured in database "
              f"({len(companies)} resolved).")
    conn.close()
    print(f"Loaded {n} companies into {settings.db_path} ({aliases} aliases from config)")


def _select_companies(conn, args) -> tuple[list[dict], list[str] | None]:
    """Resolve the company set for a collect run. Returns (companies, requested)."""
    if getattr(args, "pilot_set", False):
        companies, requested = ensure_pilot_companies(conn)
        print(f"Using Phase 3 pilot set ({len(requested)} tickers).")
        return companies, requested
    if getattr(args, "validation_set", False):
        companies, requested = ensure_validation_companies(conn)
        print(f"Using Phase 1 validation set ({len(requested)} tickers).")
        return companies, requested
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
    exclusive = (
        getattr(args, "validation_set", False),
        getattr(args, "pilot_set", False),
        bool(getattr(args, "ticker", None)),
        getattr(args, "all", False),
        bool(getattr(args, "limit", None)),
    )
    if sum(exclusive) > 1:
        raise SystemExit(
            "Use exactly one scope: --pilot-set, --validation-set, --ticker, --all, or --limit."
        )
    conn = _conn()
    if repo.count_companies(conn) == 0:
        print("Company universe is empty; loading S&P 500 first...")
        load_universe(conn)

    companies, requested = _select_companies(conn, args)
    if requested:
        found = {c["ticker"] for c in companies}
        missing = sorted(set(requested) - found)
        if missing:
            _, still_missing = upsert_tickers_from_sec(conn, missing)
            companies = repo.get_companies(conn, requested)
            if still_missing:
                print(
                    f"Not in database or SEC filers (skipped): {', '.join(still_missing)}."
                )
    if not companies:
        conn.close()
        raise SystemExit("No matching companies found. Run: ai-collect load-companies")

    companies = enrich_companies(conn, companies)
    collectors = get_collectors(args.source)
    freshness = policy_from_collect_args(args)
    if freshness is not None and freshness.enabled:
        scope = f"--stale-days {args.stale_days}" if args.stale_days is not None else ""
        if args.since:
            scope = f"{scope} --since {args.since}".strip()
        print(f"Incremental refresh ({scope}): skipping fresh ticker×source pairs.")
    totals = run_collection(
        conn, companies, collectors,
        command="collect",
        args={
            "tickers": requested,
            "all": args.all,
            "sources": args.source or SOURCE_KEYS,
            "stale_days": getattr(args, "stale_days", None),
            "since": getattr(args, "since", None),
            "force": getattr(args, "force", False),
        },
        freshness_policy=freshness,
    )
    conn.close()
    cost_line = ""
    if totals.get("estimated_api_cost_usd") is not None:
        cost_line = f", ~${totals['estimated_api_cost_usd']:.4f} est. API cost"
    skipped = totals.get("skipped") or 0
    skip_part = f", {skipped} skipped" if skipped else ""
    print(f"\nRun #{totals['run_id']}: {totals['evidence']} evidence items, "
          f"{totals['documents']} documents, {totals['ok']} ok / {totals['failed']} failed"
          f"{skip_part} in {totals['runtime_seconds']}s{cost_line}")


def cmd_analyze(args) -> None:
    conn = _conn()
    if repo.count_companies(conn) == 0:
        print("Company universe is empty; loading S&P 500 first...")
        load_universe(conn)

    query = " ".join(args.name).strip()
    result = lookup_company(conn, query)
    if result.used_sec_fallback:
        print(f"'{query}' is not in the loaded S&P 500 universe; searching all SEC filers...")
    if not result.matches:
        conn.close()
        raise SystemExit(f"No company matches {query!r}. Try the exact ticker symbol.")
    if len(result.matches) > 1:
        conn.close()
        raise SystemExit(format_ambiguous_message(query, result.matches))

    company = materialize_company(conn, result.matches[0])
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


def cmd_resolve(args) -> None:
    conn = _conn()
    query = " ".join(args.name).strip()
    result = lookup_company(conn, query)
    if result.used_sec_fallback:
        print(f"'{query}' is not in the loaded universe; matched via SEC filers.")
    if not result.matches:
        conn.close()
        raise SystemExit(f"No company matches {query!r}. Try the exact ticker symbol.")
    if len(result.matches) > 1:
        conn.close()
        raise SystemExit(format_ambiguous_message(query, result.matches))

    company = result.matches[0]
    print(f"{company['ticker']} — {company.get('company_name') or 'n/a'}")
    print(f"  CIK:             {company.get('cik') or 'n/a'}")
    print(f"  Sector:          {company.get('sector') or 'n/a'}")
    print(f"  Industry:        {company.get('industry') or 'n/a'}")
    print(f"  Identifier src:  {company.get('source_of_identifier') or 'n/a'}")
    conn.close()


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
    breakdown = report.get("outcome_breakdown") or []
    if breakdown:
        print("\nOutcome breakdown (latest status per source):")
        print(f"  {'REASON':<20} {'STATUS':<14} {'RUNS':>6}")
        for row in breakdown:
            reason = row.get("outcome_reason") or "(none)"
            print(f"  {reason:<20} {row['status']:<14} {row['runs']:>6}")
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
    orgs = github_orgs_for_ticker(ticker)
    lines.append(f"  GitHub orgs:     {', '.join(orgs) if orgs else '(none — see config/company_github_orgs.yaml)'}")
    if aliases:
        lines.append("  Aliases:")
        for row in aliases:
            lines.append(f"    - {row['alias']} ({row['alias_type']})")
    else:
        lines.append("  Aliases:         (none)")
    if statuses:
        lines.append("  Last collection status:")
        for row in statuses:
            reason = parse_outcome_reason(row.get("message"))
            detail = parse_outcome_detail(row.get("message"))
            hits = row.get("source_hits") or 0
            extra = []
            if reason:
                extra.append(f"reason={reason}")
            if hits:
                extra.append(f"hits={hits}")
            if detail:
                extra.append(detail)
            suffix = f" ({', '.join(extra)})" if extra else ""
            lines.append(
                f"    {row['source_type']:<24} {row['status']:<18} "
                f"evidence={row['evidence_count']}{suffix}"
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
    header = (
        f"{'TICKER':<8} {'SOURCE':<22} {'STATUS':<18} {'EVID':>5} {'DOCS':>5} "
        f"{'HITS':>5} {'CALLS':>6} {'REASON':<18} DETAIL"
    )
    print(header)
    for r in rows:
        reason = parse_outcome_reason(r.get("message")) or ""
        detail = parse_outcome_detail(r.get("message")) or ""
        print(
            f"{r['ticker']:<8} {r['source_type']:<22} {r['status']:<18} "
            f"{r['evidence_count']:>5} {r['documents_count']:>5} "
            f"{(r.get('source_hits') or 0):>5} {(r.get('api_calls') or 0):>6} "
            f"{reason:<18} {detail}"
        )


def cmd_retry_failed(args) -> None:
    conn = _conn()
    tickers = _normalize(args.ticker)
    collector_names = None
    if args.source:
        from .collectors import REGISTRY

        collector_names = [REGISTRY[s].name for s in args.source]
    rows = repo.failed_status_rows(conn, tickers=tickers, collector_names=collector_names)
    if args.dry_run:
        conn.close()
        print(format_retry_plan(rows))
        print(f"\n{len(rows)} pair(s) would be retried.")
        return
    targets = build_retry_targets(conn, rows, source_keys=args.source)
    conn.close()
    if not rows:
        print("No retryable failures (latest status per ticker×source).")
        return
    if not targets:
        print("No matching companies/collectors found for failed rows.")
        return
    conn = _conn()
    from .runner import run_targeted_collection

    print(f"Retrying {len(targets)} failed ticker×source pair(s)...")
    totals = run_targeted_collection(
        conn,
        targets,
        command="retry-failed",
        args={"tickers": tickers, "sources": args.source, "pairs": len(targets)},
    )
    conn.close()
    cost_line = ""
    if totals.get("estimated_api_cost_usd") is not None:
        cost_line = f", ~${totals['estimated_api_cost_usd']:.4f} est. API cost"
    print(
        f"\nRun #{totals['run_id']}: {totals['evidence']} evidence items, "
        f"{totals['documents']} documents, {totals['ok']} ok / {totals['failed']} failed "
        f"in {totals['runtime_seconds']}s{cost_line}"
    )


def cmd_verify_universe(args) -> None:
    conn = _conn()
    if repo.count_companies(conn) == 0:
        print("Company universe is empty; loading S&P 500 first...")
        load_universe(conn)
    stats = universe_stats(conn)
    spot = spot_check_tickers(conn, DEFAULT_SPOT_CHECK)
    conn.close()

    print("Universe verification (Phase 3A.1)")
    print(f"  Companies in DB:        {stats['total_companies']}")
    print(f"  With CIK:               {stats['with_cik']}")
    print(f"  With website_domain:    {stats['with_domain_db']} (config seeds: {stats['domains_configured']})")
    print(f"  GitHub orgs configured: {stats['github_orgs_configured']} tickers")
    print(f"  Pilot set ({stats['pilot_ticker_count']} tickers):")
    print(f"    domain in DB:         {stats['pilot_with_domain_db']}")
    print(f"    domain in config:     {stats['pilot_with_domain_config']}")
    print(f"    GitHub orgs:          {stats['pilot_with_github_orgs']}")
    ok_cik = stats["total_companies"] >= 490 and stats["with_cik"] == stats["total_companies"]
    print(f"  CIK gate (>=490, all):  {'PASS' if ok_cik else 'REVIEW'}")
    print()
    print("Spot-check (10 tickers):")
    for row in spot:
        if not row.get("found"):
            print(f"  {row['ticker']}: NOT IN DATABASE")
            continue
        domain = row.get("website_domain") or "n/a"
        print(
            f"  {row['ticker']}: CIK={row.get('cik') or 'n/a'}, "
            f"domain={domain}, sector={row.get('sector') or 'n/a'}"
        )


def _resolve_freshness_scope(conn, args) -> list[dict]:
    """Resolve company list for freshness / status-style commands."""
    exclusive = (
        getattr(args, "validation_set", False),
        getattr(args, "pilot_set", False),
        bool(getattr(args, "ticker", None)),
        getattr(args, "all", False),
    )
    if sum(exclusive) > 1:
        raise SystemExit(
            "Use exactly one scope: --pilot-set, --validation-set, --ticker, or --all."
        )
    if getattr(args, "pilot_set", False):
        companies, _ = ensure_pilot_companies(conn)
        return companies
    if getattr(args, "validation_set", False):
        companies, _ = ensure_validation_companies(conn)
        return companies
    if getattr(args, "ticker", None):
        return repo.get_companies(conn, _normalize(args.ticker))
    if getattr(args, "all", False) or repo.count_companies(conn) > 0:
        return repo.get_companies(conn)
    return []


def cmd_freshness(args) -> None:
    conn = _conn()
    if repo.count_companies(conn) == 0:
        conn.close()
        raise SystemExit("Company universe is empty. Run: ai-collect load-companies")
    companies = _resolve_freshness_scope(conn, args)
    if not companies:
        conn.close()
        raise SystemExit("No matching companies found.")
    report = build_freshness_report(
        conn,
        companies,
        stale_days=getattr(args, "stale_days", None),
    )
    conn.close()

    if getattr(args, "json", False):
        payload = json.dumps(report, indent=2)
        if args.output:
            write_freshness_report(Path(args.output), report)
            print(f"Wrote {args.output}")
        else:
            print(payload)
    else:
        print(format_freshness_report(report, stale_only=getattr(args, "stale_only", False)))
        if args.output:
            write_freshness_report(Path(args.output), report)
            print(f"\nJSON export: {args.output}")

    if getattr(args, "fail_on_stale", False):
        summary = report["summary"]
        if summary["stale_companies"] or summary["stale_sources"]:
            raise SystemExit(1)


def cmd_costs(args) -> None:
    conn = _conn()
    run_id = args.run_id or repo.latest_run_id(conn)
    if run_id is None:
        conn.close()
        raise SystemExit("No collection runs recorded yet. Run: ai-collect collect")
    summary = summarize_run_costs(conn, int(run_id))
    company_count = repo.count_companies(conn)
    conn.close()
    print(format_cost_report(summary))
    if args.project_full_sp500 and summary["estimated_usd"] > 0:
        pilot = 50
        per_company = summary["estimated_usd"] / pilot
        projected = per_company * company_count
        print()
        print(
            f"Projection (linear): ${per_company:.4f}/company × {company_count} companies "
            f"≈ ${projected:.2f} per full run (pilot basis: {pilot} companies)"
        )


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
    s.add_argument(
        "--validation-set",
        action="store_true",
        help="After S&P load, ensure all tickers in config/validation_companies.yaml exist (SEC fallback).",
    )
    s.add_argument(
        "--pilot-set",
        action="store_true",
        help="After S&P load, ensure all tickers in config/phase3_pilot_companies.yaml exist.",
    )
    s.set_defaults(func=cmd_load_companies)

    s = sub.add_parser("collect", help="Collect evidence for companies.")
    s.add_argument("--ticker", nargs="*", help="Tickers, e.g. MSFT NVDA ELAN. Missing tickers are upserted from SEC.")
    s.add_argument("--limit", type=int, default=None, help="Collect first N loaded companies.")
    s.add_argument("--all", action="store_true", help="Collect every loaded company.")
    s.add_argument(
        "--validation-set",
        action="store_true",
        help="Collect all tickers from config/validation_companies.yaml (Phase 1 sample).",
    )
    s.add_argument(
        "--pilot-set",
        action="store_true",
        help="Collect all tickers from config/phase3_pilot_companies.yaml (Phase 3 pilot, 50).",
    )
    s.add_argument(
        "--stale-days",
        type=int,
        default=None,
        metavar="N",
        help="Skip sources collected within N days (uses config/source_freshness_ttl.yaml per source_type).",
    )
    s.add_argument(
        "--since",
        default=None,
        metavar="YYYY-MM-DD",
        help="Skip sources last collected on or after this date.",
    )
    s.add_argument(
        "--force",
        action="store_true",
        help="Collect all requested sources ignoring freshness (--stale-days / --since).",
    )
    _add_source_flag(s)
    s.set_defaults(func=cmd_collect)

    s = sub.add_parser("analyze", help="Collect evidence for one company by name or ticker.")
    s.add_argument("name", nargs="+", help="Company name or ticker, e.g. Microsoft or MSFT")
    _add_source_flag(s)
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("resolve", help="Resolve company name/ticker to identity (no collection).")
    s.add_argument("name", nargs="+", help="Company name or ticker, e.g. Microsoft or ELAN")
    s.set_defaults(func=cmd_resolve)

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

    s = sub.add_parser("retry-failed", help="Re-run collectors for latest rate_limited/source_unavailable pairs.")
    s.add_argument("--ticker", nargs="*", help="Limit retry to these tickers.")
    s.add_argument(
        "--dry-run",
        action="store_true",
        help="List failed pairs without collecting.",
    )
    _add_source_flag(s)
    s.set_defaults(func=cmd_retry_failed)

    s = sub.add_parser("verify-universe", help="Phase 3A.1: report universe coverage and spot-check tickers.")
    s.set_defaults(func=cmd_verify_universe)

    s = sub.add_parser("costs", help="Estimated API cost for a collection run.")
    s.add_argument("--run-id", type=int, default=None, help="Collector run id (default: latest).")
    s.add_argument(
        "--project-full-sp500",
        action="store_true",
        help="Linear projection to full loaded universe from 50-ticker pilot basis.",
    )
    s.set_defaults(func=cmd_costs)

    s = sub.add_parser("freshness", help="Corpus age and per-source collection freshness (Phase 3A.6).")
    s.add_argument("--ticker", nargs="*", help="Limit to these tickers.")
    s.add_argument(
        "--validation-set",
        action="store_true",
        help="Report tickers from config/validation_companies.yaml.",
    )
    s.add_argument(
        "--pilot-set",
        action="store_true",
        help="Report tickers from config/phase3_pilot_companies.yaml.",
    )
    s.add_argument("--all", action="store_true", help="Report all loaded companies (default when no --ticker).")
    s.add_argument(
        "--stale-days",
        type=int,
        default=None,
        metavar="N",
        help="Flag companies with no evidence in N days (default: config default_stale_days).",
    )
    s.add_argument(
        "--stale-only",
        action="store_true",
        help="Show only stale companies and sources in text output.",
    )
    s.add_argument("--json", action="store_true", help="Print JSON report (machine-readable).")
    s.add_argument("--output", default=None, help="Write JSON report to this path.")
    s.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Exit 1 when any company or source is stale (for cron alerts).",
    )
    s.set_defaults(func=cmd_freshness)

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
