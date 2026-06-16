from __future__ import annotations

import argparse
import csv
from pathlib import Path

from evidence_collection.collectors import SOURCE_KEYS, get_collectors
from evidence_collection.config import settings
from evidence_collection.runner import run_collection

from .company import (
    CompanyAmbiguousError,
    CompanyNotFoundError,
    evidence_count,
    open_evidence_db,
    print_score_result,
    resolve_for_scoring,
    score_resolved_company,
)
from .scoring import compute_score_results, persist_scores


def _filter(results, tickers):
    if not tickers:
        return results
    wanted = {t.upper().replace(".", "-") for t in tickers}
    return [r for r in results if r.ticker in wanted]


def _resolve_company_arg(conn, company: str) -> dict:
    try:
        return resolve_for_scoring(conn, company)
    except CompanyNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    except CompanyAmbiguousError as exc:
        raise SystemExit(str(exc)) from exc


def _score_one(conn, company: dict):
    try:
        return score_resolved_company(conn, company)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def cmd_score(args) -> None:
    conn = open_evidence_db(args.db)
    if args.company:
        company = _resolve_company_arg(conn, args.company)
        results = [_score_one(conn, company)]
    else:
        results = _filter(compute_score_results(conn), args.ticker)
        if not results:
            conn.close()
            print("No scored companies. Collect evidence first with `ai-collect collect`.")
            return
    for r in results:
        print_score_result(r)
    if args.persist:
        n = persist_scores(conn, results)
        print(f"\nPersisted {n} score rows ({results[0].formula_version}).")
    conn.close()


def cmd_run(args) -> None:
    conn = open_evidence_db(args.db)
    company = _resolve_company_arg(conn, args.company)
    ticker = company["ticker"]
    needs_collect = args.collect or evidence_count(conn, ticker) == 0
    if needs_collect:
        print(f"Collecting evidence for {ticker} — {company.get('company_name') or 'n/a'}")
        totals = run_collection(
            conn,
            [company],
            get_collectors(args.source),
            command="run",
            args={
                "company": args.company,
                "ticker": ticker,
                "sources": args.source or SOURCE_KEYS,
                "collect": args.collect,
            },
        )
        print(
            f"Collected {totals['evidence']} evidence items, {totals['documents']} documents "
            f"({totals['ok']} ok / {totals['failed']} failed)."
        )
    result = _score_one(conn, company)
    print_score_result(result)
    if args.persist:
        n = persist_scores(conn, [result])
        print(f"\nPersisted {n} score row ({result.formula_version}).")
    conn.close()


def cmd_export_scores(args) -> None:
    conn = open_evidence_db(args.db)
    if args.company:
        company = _resolve_company_arg(conn, args.company)
        results = [_score_one(conn, company)]
    else:
        results = _filter(compute_score_results(conn), args.ticker)
    if args.persist:
        persist_scores(conn, results)
    conn.close()
    rows = [r.to_row() for r in results]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["ticker"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} score rows to {out}"
          + (" (persisted to scores table)" if args.persist else ""))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai-score", description="Inference layer (MVP scorer).")
    p.add_argument("--db", default=settings.db_path, help="Path to the evidence SQLite database.")
    sub = p.add_subparsers(required=True, dest="command")

    s = sub.add_parser("score", help="Print AI Depth Scores with per-driver explanation.")
    target = s.add_mutually_exclusive_group()
    target.add_argument("--ticker", nargs="*")
    target.add_argument("--company", help="Company name or ticker (resolves via DB + SEC).")
    s.add_argument("--persist", action="store_true", help="Also write versioned rows to the scores table.")
    s.set_defaults(func=cmd_score)

    s = sub.add_parser(
        "run",
        help="Resolve company, collect evidence if missing (or --collect), then score.",
    )
    s.add_argument("--company", required=True, help="Company name or ticker.")
    s.add_argument(
        "--collect",
        action="store_true",
        help="Re-collect even when evidence already exists.",
    )
    s.add_argument("--source", nargs="*", choices=SOURCE_KEYS, help="Limit collectors.")
    s.add_argument("--persist", action="store_true", help="Write versioned row to scores table.")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("export-scores", help="Export AI Depth Scores to CSV.")
    s.add_argument("--output", default="data/exports/ai_depth_scores.csv")
    target = s.add_mutually_exclusive_group()
    target.add_argument("--ticker", nargs="*")
    target.add_argument("--company", help="Company name or ticker.")
    s.add_argument("--persist", action="store_true", help="Also write versioned rows to the scores table.")
    s.set_defaults(func=cmd_export_scores)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
