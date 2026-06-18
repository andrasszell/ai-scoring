from __future__ import annotations

import os
from pathlib import Path

import yaml

from ..db import repository as repo
from .domains import apply_domains
from .sp500 import fetch_sec_companies, normalize_ticker
from .validation import validation_tickers


def default_pilot_path() -> Path:
    env_path = os.getenv("PHASE3_PILOT_COMPANIES_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[3]
    candidate = project_root / "config" / "phase3_pilot_companies.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "phase3_pilot_companies.yaml"


def load_pilot_entries(path: Path | None = None) -> list[dict]:
    """Load pilot company entries from config/phase3_pilot_companies.yaml."""
    yaml_path = path or default_pilot_path()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"phase3 pilot config not found: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"phase3_pilot_companies must be a mapping: {yaml_path}")
    entries = raw.get("companies") or []
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"phase3_pilot_companies.companies must be a non-empty list: {yaml_path}")
    out: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"each pilot company must be a mapping: {entry!r}")
        ticker = normalize_ticker(str(entry.get("ticker") or ""))
        if not ticker:
            raise ValueError(f"pilot company missing ticker: {entry!r}")
        if ticker in seen:
            raise ValueError(f"duplicate pilot ticker: {ticker}")
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


def pilot_tickers(path: Path | None = None) -> list[str]:
    return [e["ticker"] for e in load_pilot_entries(path)]


def ensure_pilot_companies(conn, path: Path | None = None) -> tuple[list[dict], list[str]]:
    """Ensure all pilot tickers exist in the DB; SEC fallback for missing rows."""
    tickers = pilot_tickers(path)
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
                "pilot tickers not found in database or SEC filers: "
                + ", ".join(sorted(still_missing))
            )
    companies = repo.get_companies(conn, tickers)
    return companies, tickers


def pilot_includes_validation(path: Path | None = None) -> bool:
    """True when every validation ticker is a subset of the pilot list."""
    pilot = set(pilot_tickers(path))
    return set(validation_tickers()).issubset(pilot)
