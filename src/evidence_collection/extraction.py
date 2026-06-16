from __future__ import annotations

import hashlib
import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from .config import AI_KEYWORDS

# Some SEC primary documents are XML served as filings; we parse them as HTML to
# extract readable text, so silence the advisory warning.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Whole-word/phrase matching, longest first so phrases win over their sub-words.
# Word boundaries prevent false positives like "llm" inside "installments".
_SORTED_KEYWORDS = sorted(AI_KEYWORDS, key=len, reverse=True)
_KEYWORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _SORTED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def content_hash(text: str) -> str:
    """Stable hash for raw text / API responses (deduplication, reproducibility)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n|(?<=\.)\s{2,}", text)
    return [re.sub(r"\s+", " ", c).strip() for c in chunks if len(c.strip()) > 80]


def keyword_hits(text: str) -> list[str]:
    return sorted(set(m.group(0).lower() for m in _KEYWORD_RE.finditer(text)))


def candidate_paragraphs(text: str, limit: int = 40) -> list[dict]:
    """High-recall candidate AI evidence: paragraphs containing AI keywords.

    Per the Implementation Plan (§10), keyword hits create *candidate evidence*,
    never scores. Interpretation is the inference layer's job.
    """
    rows: list[dict] = []
    seen: set[str] = set()
    for para in split_paragraphs(text):
        hits = keyword_hits(para)
        if not hits:
            continue
        key = para[:300]
        if key in seen:
            continue
        seen.add(key)
        rows.append({"text": para[:2500], "keywords": hits})
        if len(rows) >= limit:
            break
    return rows
