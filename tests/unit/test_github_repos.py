import requests

from evidence_collection.db import repository as repo
from evidence_collection.collectors.github_repos import GitHubReposCollector
from evidence_collection.config import settings
from evidence_collection.models import CollectionContext
from evidence_collection.outcomes import OutcomeReason
from evidence_collection.status import CollectionStatus

COMPANY = {"ticker": "MSFT", "company_name": "Microsoft Corporation", "company_id": "MSFT"}
UNKNOWN = {"ticker": "ZZZZ", "company_name": "Unknown Co", "company_id": "ZZZZ"}


class _FakeResponse:
    def __init__(self, payload, text=""):
        self._payload = payload
        self.text = text or str(payload)
        self.status_code = 200

    def json(self):
        return self._payload


def _github_settings(token=""):
    return type("S", (), {"github_token": token})()


def test_github_source_empty_when_no_orgs_configured(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.github_orgs_for_ticker",
        lambda ticker: [],
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = GitHubReposCollector().collect(ctx, UNKNOWN)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY
    assert "no GitHub orgs" in (result.message or "")


def test_github_source_empty_when_search_has_no_hits(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.github_orgs_for_ticker",
        lambda ticker: ["microsoft"],
    )
    monkeypatch.setattr("evidence_collection.collectors.github_repos.settings", _github_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.get",
        lambda *a, **k: _FakeResponse({"total_count": 0, "items": []}, text='{"total_count":0}'),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = GitHubReposCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_github_filtered_to_zero_when_repos_lack_ai_keywords(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.github_orgs_for_ticker",
        lambda ticker: ["microsoft"],
    )
    monkeypatch.setattr("evidence_collection.collectors.github_repos.settings", _github_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.get",
        lambda *a, **k: _FakeResponse(
            {
                "total_count": 2,
                "items": [
                    {
                        "full_name": "microsoft/vscode",
                        "name": "vscode",
                        "description": "Editor",
                        "html_url": "https://github.com/microsoft/vscode",
                        "pushed_at": "2024-01-01T00:00:00Z",
                        "topics": [],
                    }
                ],
            },
            text="{}",
        ),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = GitHubReposCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.source_hits == 2


def test_github_success_inserts_matching_repos(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.github_orgs_for_ticker",
        lambda ticker: ["microsoft"],
    )
    monkeypatch.setattr("evidence_collection.collectors.github_repos.settings", _github_settings("ghp_test"))
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.get",
        lambda *a, **k: _FakeResponse(
            {
                "total_count": 1,
                "items": [
                    {
                        "full_name": "microsoft/generative-ai",
                        "name": "generative-ai",
                        "description": "Samples for generative AI and machine learning",
                        "html_url": "https://github.com/microsoft/generative-ai",
                        "pushed_at": "2024-06-15T12:00:00Z",
                        "topics": ["llm"],
                        "stargazers_count": 100,
                        "language": "Python",
                    }
                ],
            },
            text="{}",
        ),
    )
    repo.upsert_companies(conn, [COMPANY])
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = GitHubReposCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.SUCCESS
    assert result.evidence_count == 1
    rows = conn.execute(
        "SELECT evidence_title, source_date FROM evidence_items WHERE ticker='MSFT' AND collector_name='github_repos'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["evidence_title"] == "microsoft/generative-ai"
    assert rows[0]["source_date"] == "2024-06-15"


def test_github_rate_limited(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.github_repos.github_orgs_for_ticker",
        lambda ticker: ["microsoft"],
    )
    monkeypatch.setattr("evidence_collection.collectors.github_repos.settings", _github_settings())

    def raise_429(*a, **k):
        response = type("R", (), {"status_code": 429, "text": "rate limit"})()
        err = requests.HTTPError("429 Client Error")
        err.response = response
        raise err

    monkeypatch.setattr("evidence_collection.collectors.github_repos.get", raise_429)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = GitHubReposCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.RATE_LIMITED
