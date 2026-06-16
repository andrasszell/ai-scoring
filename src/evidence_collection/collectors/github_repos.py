from __future__ import annotations

from ..config import settings
from ..dates import normalize_github_datetime
from ..db import repository as repo
from ..extraction import content_hash, keyword_hits
from ..http import get, http_error_status
from ..models import CollectionContext, CollectorResult, collector_result
from ..outcomes import OutcomeReason
from ..status import CollectionStatus
from ..universe.github_orgs import github_orgs_for_ticker
from .base import Collector

GITHUB_SEARCH = "https://api.github.com/search/repositories"
# GitHub search query length is limited; keep a compact AI term set.
AI_SEARCH_QUERY = (
    "machine learning OR artificial intelligence OR deep learning OR "
    "large language model OR neural network OR generative ai"
)
MAX_ORGS = 3
MAX_REPOS_PER_ORG = 20
MAX_EVIDENCE_ROWS = 25


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _repo_search_text(repo: dict) -> str:
    topics = repo.get("topics") or []
    parts = [repo.get("name") or "", repo.get("description") or "", " ".join(topics)]
    return " ".join(p for p in parts if p)


def _repo_matches_ai(repo: dict) -> bool:
    return bool(keyword_hits(_repo_search_text(repo)))


class GitHubReposCollector(Collector):
    """Public GitHub repositories with AI-related activity for configured org slugs.

    Org mapping lives in config/company_github_orgs.yaml (entity metadata). Without
    configured orgs the collector reports source_empty — it does not guess org names.
    """

    name = "github_repos"
    platform_id = "github_repos"
    version = "1.0.0"
    source_type = "github_repository"
    source_name = "GitHub"

    def collect(self, ctx: CollectionContext, company: dict) -> CollectorResult:
        conn = ctx.conn
        ticker = company["ticker"]
        orgs = github_orgs_for_ticker(ticker)[:MAX_ORGS]
        if not orgs:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="no GitHub orgs configured for ticker",
            )

        repo.delete_evidence(conn, ticker, self.name)
        rows: list[dict] = []
        api_calls = 0
        source_hits = 0
        candidates_seen = 0
        headers = _github_headers()

        for org in orgs:
            query = f"org:{org} ({AI_SEARCH_QUERY})"
            params = {"q": query, "sort": "updated", "order": "desc", "per_page": MAX_REPOS_PER_ORG}
            try:
                resp = get(GITHUB_SEARCH, params=params, headers=headers)
                data = resp.json()
            except Exception as exc:  # noqa: BLE001
                code = http_error_status(exc)
                status = CollectionStatus.RATE_LIMITED if code == 429 else CollectionStatus.SOURCE_UNAVAILABLE
                return CollectorResult(status, message=f"error: {exc}", api_calls=api_calls)

            api_calls += 1
            repo.save_raw_response(
                conn,
                ticker=ticker,
                source_type=self.source_type,
                collector_name=self.name,
                collector_version=self.version,
                request_url=GITHUB_SEARCH,
                request_params=query,
                status_code=getattr(resp, "status_code", None),
                response_text=resp.text[:200_000],
                content_hash=content_hash(resp.text),
            )

            items = data.get("items", []) or []
            total = int(data.get("total_count") or 0)
            source_hits += total
            candidates_seen += len(items)

            for item in items:
                if not _repo_matches_ai(item):
                    continue
                full_name = item.get("full_name") or item.get("name") or ""
                if not full_name:
                    continue
                description = (item.get("description") or "").strip()
                topics = item.get("topics") or []
                evidence_text = f"{full_name}. {description}"
                if topics:
                    evidence_text = f"{evidence_text} Topics: {', '.join(topics)}"
                source_date, date_provenance = normalize_github_datetime(item.get("pushed_at"))
                rows.append(
                    self.make_evidence(
                        company,
                        evidence_text=evidence_text[:2500],
                        source_url=item.get("html_url"),
                        source_date=source_date,
                        evidence_title=full_name,
                        metadata={
                            "github_org": org,
                            "full_name": full_name,
                            "topics": topics,
                            "stargazers_count": item.get("stargazers_count"),
                            "language": item.get("language"),
                            "date_provenance": date_provenance,
                        },
                    )
                )
                if len(rows) >= MAX_EVIDENCE_ROWS:
                    break
            if len(rows) >= MAX_EVIDENCE_ROWS:
                break

        inserted = repo.insert_evidence(conn, rows)
        if source_hits == 0 and candidates_seen == 0:
            return collector_result(
                CollectionStatus.NO_RESULTS,
                outcome_reason=OutcomeReason.SOURCE_EMPTY,
                message="GitHub search returned no repositories",
                api_calls=api_calls,
            )
        if inserted:
            return collector_result(
                CollectionStatus.SUCCESS,
                evidence_count=inserted,
                api_calls=api_calls,
                source_hits=source_hits,
                candidates_after_filter=inserted,
            )
        return collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
            message="repositories returned but none matched AI keyword filter",
            api_calls=api_calls,
            source_hits=max(source_hits, candidates_seen),
            candidates_after_filter=0,
        )
