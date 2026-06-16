#!/usr/bin/env python3
"""Print platform registry tables as Markdown (for syncing data-sources.md).

Usage:
    python scripts/sync_platform_docs.py
    python scripts/sync_platform_docs.py --all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evidence_collection.platforms import load_registry  # noqa: E402


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _auth_label(env_key: str, required: bool) -> str:
    if not env_key:
        return "—"
    label = f"`{env_key}`"
    return f"{label} (required)" if required else f"{label} (optional)"


def print_loaders(registry_path: Path | None = None) -> None:
    registry = load_registry(registry_path)
    print("### Company universe loaders\n")
    print("| ID | Display name | Vendor | Env | Phase | Enabled | CLI |")
    print("|---|---|---|---|---|---|---|")
    for loader in registry.loaders:
        print(
            f"| `{loader.id}` | {loader.display_name} | {loader.vendor} | "
            f"{_auth_label(loader.auth.env_key, loader.auth.required)} | "
            f"{loader.phase} | {_yes_no(loader.enabled)} | `{loader.cli_command or '—'}` |"
        )
    print()


def print_platforms(registry_path: Path | None = None, *, include_disabled: bool = False) -> None:
    registry = load_registry(registry_path)
    platforms = list(registry.platforms)
    if not include_disabled:
        platforms = [p for p in platforms if p.enabled]
    print("### Evidence platforms\n")
    print(
        "| ID | Collector | CLI | `source_type` | Vendor | Env | Phase | Enabled | "
        "Category | Reliability | Conf. | Cost |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for p in platforms:
        print(
            f"| `{p.id}` | `{p.collector}` | `{p.cli_source}` | `{p.source_type}` | "
            f"{p.display_name} | {_auth_label(p.auth.env_key, p.auth.required)} | "
            f"{p.phase} | {_yes_no(p.enabled)} | `{p.source_category}` | "
            f"`{p.source_reliability}` | {p.confidence_initial:.2f} | `{p.cost_model}` |"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Print platform registry as Markdown tables.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "config" / "platforms.yaml",
        help="Path to platforms.yaml",
    )
    parser.add_argument("--all", action="store_true", help="Include disabled platforms.")
    args = parser.parse_args()
    print_loaders(args.registry)
    print_platforms(args.registry, include_disabled=args.all)


if __name__ == "__main__":
    main()
