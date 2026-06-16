from __future__ import annotations

import os
from pathlib import Path

import yaml


def default_github_orgs_path() -> Path:
    env_path = os.getenv("COMPANY_GITHUB_ORGS_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[3]
    candidate = project_root / "config" / "company_github_orgs.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "company_github_orgs.yaml"


def load_company_github_orgs(path: Path | None = None) -> dict[str, list[str]]:
    """Load ticker → GitHub org slug list from config/company_github_orgs.yaml."""
    orgs_path = path or default_github_orgs_path()
    if not orgs_path.is_file():
        return {}
    raw = yaml.safe_load(orgs_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"company_github_orgs must be a mapping: {orgs_path}")
    out: dict[str, list[str]] = {}
    for ticker, orgs in raw.items():
        if str(ticker).startswith("#"):
            continue
        key = str(ticker).strip().upper().replace(".", "-")
        if not key:
            continue
        if orgs is None:
            out[key] = []
            continue
        if not isinstance(orgs, list):
            raise ValueError(f"orgs for {key} must be a list: {orgs_path}")
        slugs = [str(o).strip() for o in orgs if str(o).strip()]
        out[key] = slugs
    return out


def github_orgs_for_ticker(ticker: str, mapping: dict[str, list[str]] | None = None) -> list[str]:
    """Return configured GitHub org slugs for a ticker (may be empty)."""
    orgs = mapping if mapping is not None else load_company_github_orgs()
    return list(orgs.get((ticker or "").upper().replace(".", "-"), []))
