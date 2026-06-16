from __future__ import annotations

import os
from pathlib import Path

import yaml

from ..db import repository as repo
from .domains import apply_domains
from .sp500 import fetch_sec_companies, normalize_ticker


def default_validation_path() -> Path:
    env_path = os.getenv("VALIDATION_COMPANIES_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[3]
    candidate = project_root / "config" / "validation_companies.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "validation_companies.yaml"


def load_validation_entries(path: Path | None = None) -> list[dict]:
    """Load validation company entries from config/validation_companies.yaml."""
    yaml_path = path or default_validation_path()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"validation companies config not found: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"validation_companies must be a mapping: {yaml_path}")
    entries = raw.get("companies") or []
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"validation_companies.companies must be a non-empty list: {yaml_path}")
    out: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"each validation company must be a mapping: {entry!r}")
        ticker = normalize_ticker(str(entry.get("ticker") or ""))
        if not ticker:
            raise ValueError(f"validation company missing ticker: {entry!r}")
        if ticker in seen:
            raise ValueError(f"duplicate validation ticker: {ticker}")
        seen.add(ticker)
        out.append(
            {
                "ticker": ticker,
                "group": str(entry.get("group") or "unknown"),
                "sector": entry.get("sector"),
                "note": entry.get("note"),
            }
        )
    return out


def validation_tickers(path: Path | None = None) -> list[str]:
    return [e["ticker"] for e in load_validation_entries(path)]


def ensure_validation_companies(conn, path: Path | None = None) -> tuple[list[dict], list[str]]:
    """Ensure all validation tickers exist in the DB; SEC fallback for missing rows."""
    tickers = validation_tickers(path)
    existing = repo.get_companies(conn, tickers)
    found = {c["ticker"] for c in existing}
    missing = [t for t in tickers if t not in found]
    if missing:
        sec_by_ticker = {r["ticker"]: r for r in fetch_sec_companies()}
        to_upsert: list[dict] = []
        still_missing: list[str] = []
        for ticker in missing:
            row = sec_by_ticker.get(ticker)
            if row is None:
                still_missing.append(ticker)
                continue
            to_upsert.append(dict(row))
        if to_upsert:
            repo.upsert_companies(conn, apply_domains(to_upsert))
        found_after = {c["ticker"] for c in repo.get_companies(conn, tickers)}
        still_missing.extend(t for t in missing if t not in found_after and t not in still_missing)
        if still_missing:
            raise ValueError(
                "validation tickers not found in database or SEC filers: "
                + ", ".join(sorted(still_missing))
            )
    companies = repo.get_companies(conn, tickers)
    return companies, tickers
