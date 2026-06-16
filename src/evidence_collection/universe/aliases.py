from __future__ import annotations

import os
from pathlib import Path

import yaml

from ..db import repository as repo


def default_aliases_path() -> Path:
    env_path = os.getenv("COMPANY_ALIASES_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[3]
    candidate = project_root / "config" / "company_aliases.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "company_aliases.yaml"


def load_company_aliases(path: Path | None = None) -> list[dict]:
    """Load alias rows from config/company_aliases.yaml."""
    aliases_path = path or default_aliases_path()
    if not aliases_path.is_file():
        return []
    raw = yaml.safe_load(aliases_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"company_aliases must be a mapping: {aliases_path}")
    rows: list[dict] = []
    for ticker, entries in raw.items():
        if str(ticker).startswith("#"):
            continue
        if not isinstance(entries, list):
            raise ValueError(f"aliases for {ticker!r} must be a list")
        norm_ticker = str(ticker).strip().upper().replace(".", "-")
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"{norm_ticker}[{i}]: must be a mapping")
            alias = str(entry.get("alias") or "").strip()
            alias_type = str(entry.get("alias_type") or "brand").strip()
            if not alias:
                raise ValueError(f"{norm_ticker}[{i}]: missing alias")
            rows.append(
                {
                    "ticker": norm_ticker,
                    "alias": alias,
                    "alias_type": alias_type,
                }
            )
    return rows


def seed_company_aliases(conn, path: Path | None = None, *, source: str | None = None) -> int:
    """Insert aliases from YAML into company_aliases (idempotent). Skips unknown tickers."""
    source_label = source or "config/company_aliases.yaml"
    rows = load_company_aliases(path)
    processed = 0
    for row in rows:
        exists = conn.execute(
            "SELECT 1 FROM companies WHERE ticker=? LIMIT 1",
            (row["ticker"],),
        ).fetchone()
        if not exists:
            continue
        repo.insert_alias(conn, row["ticker"], row["alias"], row["alias_type"], source_label)
        processed += 1
    return processed
