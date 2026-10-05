from unittest.mock import Mock

import pytest
import requests

from orbshacker import quest_fetch as fetch


def response(status, body, headers=None):
    """Create a mock HTTP response with the supplied status and body."""
    result = Mock(status_code=status, headers=headers or {})
    result.json.return_value = body
    return result


def setup(monkeypatch, responses):
    """Mock account requests and record rate-limit sleep intervals."""
    monkeypatch.setenv("Authorization", "test-only")
    get = Mock(side_effect=responses)
    monkeypatch.setattr(requests, "get", get)
    sleeps = []
    monkeypatch.setattr(fetch.time, "sleep", sleeps.append)
    return get, sleeps


def test_retry_uses_longest_server_delay(monkeypatch):
    """Verify that retry uses longest server delay."""
    limited = response(429, {"retry_after": 2}, {"Retry-After": "4"})
    get, sleeps = setup(monkeypatch, [limited, response(200, {"quests": []})])
    assert fetch.fetch_quests() == {"quests": []}
    assert sleeps == [4]
    assert get.call_count == 2
    limited.close.assert_called_once()


def test_persistent_rate_limit_is_bounded(monkeypatch):
    """Verify that persistent rate limit is bounded."""
    get, sleeps = setup(
        monkeypatch, [response(429, {"retry_after": 1}) for _ in range(3)]
    )
    with pytest.raises(ValueError, match="429"):
        fetch.fetch_quests()
    assert get.call_count == 3
    assert sleeps == [1, 1]


def test_long_limit_does_not_retry_early(monkeypatch):
    """Verify that long limit does not retry early."""
    get, sleeps = setup(monkeypatch, [response(429, {"retry_after": 180})])
    with pytest.raises(ValueError, match="180"):
        fetch.fetch_quests()
    assert get.call_count == 1
    assert not sleeps


def test_unauthorized_does_not_retry(monkeypatch):
    """Verify that unauthorized does not retry."""
    denied = response(401, {})
    denied.raise_for_status.side_effect = requests.HTTPError("401")
    get, sleeps = setup(monkeypatch, [denied])
    with pytest.raises(requests.HTTPError):
        fetch.fetch_quests()
    assert get.call_count == 1
    assert not sleeps
