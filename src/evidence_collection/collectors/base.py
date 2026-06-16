from __future__ import annotations

import json
from abc import ABC, abstractmethod

from ..extraction import content_hash
from ..models import CollectionContext, CollectorResult
from ..sources import profile_for, refine_for_url
from ..status import CollectionStatus


class Collector(ABC):
    """Base class for every source connector.

    Each collector is independently testable, declares a name/version (so evidence
    is traceable to the exact code that produced it), and returns a CollectorResult
    rather than raising — a single source failure must never abort a whole run.
    """

    name: str = "base"
    version: str = "0.0.0"
    source_type: str = "unknown"
    source_name: str | None = None

    @abstractmethod
    def collect(self, ctx: CollectionContext, company: dict) -> CollectorResult:
        ...

    def make_evidence(
        self,
        company: dict,
        *,
        evidence_text: str,
        source_url: str | None = None,
        source_date: str | None = None,
        source_name: str | None = None,
        evidence_title: str | None = None,
        evidence_context: str | None = None,
        raw_document_id: int | None = None,
        metadata: dict | None = None,
        language: str = "en",
    ) -> dict:
        """Build an evidence row that conforms to the Evidence Object Standard (§8)
        and the Coding Standards data model (§4/§6)."""
        text = (evidence_text or "")[:2500]
        profile = profile_for(self.source_type)
        profile = refine_for_url(profile, source_url, company.get("website_domain"))
        return {
            "company_id": company.get("company_id") or company["ticker"],
            "ticker": company["ticker"],
            "company_name": company.get("company_name"),
            "source_type": self.source_type,
            "source_name": source_name or self.source_name or self.name,
            "source_url": source_url,
            "source_date": source_date,
            "evidence_text": text,
            "evidence_title": evidence_title,
            "evidence_context": evidence_context,
            "raw_document_id": raw_document_id,
            "collector_name": self.name,
            "collector_version": self.version,
            "language": language,
            "metadata_json": json.dumps(metadata or {}, default=str),
            "collection_status": CollectionStatus.SUCCESS,
            "raw_hash": content_hash(text),
            "confidence_initial": profile.confidence_initial,
            "source_category": profile.category,
            "source_reliability": profile.reliability,
        }
