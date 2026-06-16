from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path

from .scoring import compute_score_results, persist_scores


DB_PATH = os.getenv("AI_DEPTH_DB", "data/evidence.sqlite")


def _conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _filter(results, tickers):
    if not tickers:
        return results
    wanted = {t.upper().replace(".", "-") for t in tickers}
    return [r for r in results if r.ticker in wanted]


def cmd_score(args) -> None:
    conn = _conn(args.db)
    results = _filter(compute_score_results(conn), args.ticker)
    if not results:
        conn.close()
        print("No scored companies. Collect evidence first with `ai-collect collect`.")
        return
    for r in results:
        print(f"\n{r.ticker} — {r.company_name}: {r.score_value} / 100  "
              f"[{r.score_type} {r.formula_version}]")
        for name, exp in r.explanation.items():
            print(f"    {exp['points']:>6}  {name:<14} "
                  f"(count={exp['evidence_count']}, cap={exp['cap']}, weight={exp['weight']})")
        print(f"    inputs: {len(r.input_evidence_ids)} evidence items")
    if args.persist:
        n = persist_scores(conn, results)
        print(f"\nPersisted {n} score rows ({results[0].formula_version}).")
    conn.close()


def cmd_export_scores(args) -> None:
    conn = _conn(args.db)
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
    p.add_argument("--db", default=DB_PATH, help="Path to the evidence SQLite database.")
    sub = p.add_subparsers(required=True, dest="command")

    s = sub.add_parser("score", help="Print AI Depth Scores with per-driver explanation.")
    s.add_argument("--ticker", nargs="*")
    s.add_argument("--persist", action="store_true", help="Also write versioned rows to the scores table.")
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("export-scores", help="Export AI Depth Scores to CSV.")
    s.add_argument("--output", default="data/exports/ai_depth_scores.csv")
    s.add_argument("--ticker", nargs="*")
    s.add_argument("--persist", action="store_true", help="Also write versioned rows to the scores table.")
    s.set_defaults(func=cmd_export_scores)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
