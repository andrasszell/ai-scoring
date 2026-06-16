from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# Candidate AI keyword/phrases for high-recall evidence detection (NOT scoring).
# Matched as whole words/phrases (see extraction.keyword_hits).
AI_KEYWORDS = [
    "artificial intelligence",
    "generative ai",
    "gen ai",
    "machine learning",
    "deep learning",
    "large language model",
    "large language models",
    "llm",
    "foundation model",
    "neural network",
    "natural language processing",
    "computer vision",
    "predictive analytics",
    "predictive model",
    "recommendation engine",
    "mlops",
    "ai assistant",
    "ai agent",
    "autonomous",
    "automation",
    "copilot",
]

# Default collection universe: the largest S&P 500 companies by index weight.
# Used by `collect` when no --ticker/--all/--limit is given.
DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "AVGO",
    "TSLA",
    "BRK-B",
    "JPM",
]


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(os.getenv("AI_DEPTH_DB", "data/evidence.sqlite"))
    raw_dir: Path = Path(os.getenv("AI_DEPTH_RAW_DIR", "data/raw"))
    export_dir: Path = Path(os.getenv("AI_DEPTH_EXPORT_DIR", "data/exports"))
    sec_user_agent: str = os.getenv("SEC_USER_AGENT", "ai-collect contact@example.com")
    fmp_api_key: str = os.getenv("FMP_API_KEY", "")
    serpapi_api_key: str = os.getenv("SERPAPI_API_KEY", "")
    semantic_scholar_api_key: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    patentsview_api_key: str = os.getenv("PATENTSVIEW_API_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    max_candidate_paragraphs: int = int(os.getenv("MAX_CANDIDATE_PARAGRAPHS", "40"))
    log_level: str = os.getenv("AI_DEPTH_LOG_LEVEL", "INFO")
    platforms_yaml: Path | None = (
        Path(p) if (p := os.getenv("PLATFORMS_YAML", "").strip()) else None
    )


settings = Settings()
