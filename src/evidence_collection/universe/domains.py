from __future__ import annotations

import os
from pathlib import Path

import yaml

from ..config import DEFAULT_TICKERS


def default_domains_path() -> Path:
    env_path = os.getenv("COMPANY_DOMAINS_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[3]
    candidate = project_root / "config" / "company_domains.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "company_domains.yaml"


def load_company_domains(path: Path | None = None) -> dict[str, str]:
    """Load ticker → website_domain map from config/company_domains.yaml."""
    domains_path = path or default_domains_path()
    if not domains_path.is_file():
        return {}
    raw = yaml.safe_load(domains_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"company_domains must be a mapping: {domains_path}")
    out: dict[str, str] = {}
    for ticker, domain in raw.items():
        if ticker.startswith("#") or domain is None:
            continue
        key = str(ticker).strip().upper().replace(".", "-")
        value = str(domain).strip().lower().removeprefix("www.")
        if key and value:
            out[key] = value
    return out


def domain_for_ticker(ticker: str, domains: dict[str, str] | None = None) -> str | None:
    mapping = domains if domains is not None else load_company_domains()
    return mapping.get((ticker or "").upper().replace(".", "-"))


def apply_domains(rows: list[dict], domains: dict[str, str] | None = None) -> list[dict]:
    """Attach website_domain when known and not already set on the row."""
    mapping = domains if domains is not None else load_company_domains()
    out: list[dict] = []
    for row in rows:
        updated = dict(row)
        ticker = (updated.get("ticker") or "").upper().replace(".", "-")
        if not updated.get("website_domain") and ticker in mapping:
            updated["website_domain"] = mapping[ticker]
        out.append(updated)
    return out


def default_tickers_have_domains(domains: dict[str, str] | None = None) -> bool:
    mapping = domains if domains is not None else load_company_domains()
    return all(ticker in mapping for ticker in DEFAULT_TICKERS)
