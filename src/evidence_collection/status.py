from __future__ import annotations


class CollectionStatus:
    """Canonical collector status values (Implementation Plan §12).

    Distinguishing these is essential downstream: "absence of evidence is not
    evidence of absence". The inference team must know *why* a pillar is empty.
    """

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    API_KEY_MISSING = "api_key_missing"
    API_LIMIT_REACHED = "api_limit_reached"
    SOURCE_UNAVAILABLE = "source_unavailable"
    PARSE_FAILED = "parse_failed"
    COMPANY_NOT_FOUND = "company_not_found"
    AMBIGUOUS_COMPANY = "ambiguous_company"
    RATE_LIMITED = "rate_limited"
    SKIPPED = "skipped"

    ALL = frozenset(
        {
            SUCCESS,
            NO_RESULTS,
            API_KEY_MISSING,
            API_LIMIT_REACHED,
            SOURCE_UNAVAILABLE,
            PARSE_FAILED,
            COMPANY_NOT_FOUND,
            AMBIGUOUS_COMPANY,
            RATE_LIMITED,
            SKIPPED,
        }
    )
