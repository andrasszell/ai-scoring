import requests
from tenacity import RetryError
from unittest.mock import MagicMock

from evidence_collection.http import http_error_status


def test_http_error_status_from_http_error():
    response = type("R", (), {"status_code": 429})()
    err = requests.HTTPError("429")
    err.response = response
    assert http_error_status(err) == 429


def test_http_error_status_from_retry_error():
    response = type("R", (), {"status_code": 503})()
    inner = requests.HTTPError("503")
    inner.response = response
    attempt = MagicMock()
    attempt.failed = True
    attempt.exception.return_value = inner
    assert http_error_status(RetryError(attempt)) == 503


def test_http_error_status_returns_none_for_generic_error():
    assert http_error_status(RuntimeError("network")) is None
