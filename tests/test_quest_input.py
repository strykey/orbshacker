from datetime import datetime, timezone

import pytest

from orbshacker.quest_fetch import normalize_quests
from orbshacker.quest_input import receive_payload

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)


def sample():
    """Return a fictional normalized quest with a fixed time window."""
    return {
        "schema_version": 1,
        "fetched_at": NOW.isoformat(),
        "quests": [
            {
                "quest_id": "example-quest",
                "application": {"id": "example-app", "name": "Example Game"},
                "starts_at": "2026-10-01T00:00:00Z",
                "expires_at": "2026-10-10T00:00:00Z",
                "enrolled": True,
                "completed": False,
                "claimed": False,
                "task_join_operator": "and",
                "tasks": [
                    {"event": "EXAMPLE_EVENT", "target": 900, "progress": None}
                ],
            }
        ],
    }


def test_valid_data_is_never_execution_approval():
    """Verify that valid data is never execution approval."""
    report = receive_payload(sample(), NOW)
    assert report["mode"] == "validate_only"
    assert report["results"][0]["status"] == "needs_review"
    assert report["results"][0]["tasks"][0]["progress"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("enrolled", "false"),
        ("expires_at", "bad"),
        ("starts_at", "2026-10-01T00:00:00"),
        ("tasks", []),
    ],
)
def test_invalid_rows(field, value):
    """Verify that invalid rows."""
    payload = sample()
    payload["quests"][0][field] = value
    assert receive_payload(payload, NOW)["results"][0]["status"] == "invalid"


def test_expiry_and_duplicates():
    """Verify that expiry and duplicates."""
    payload = sample()
    payload["quests"][0]["expires_at"] = NOW.isoformat()
    payload["quests"].append(payload["quests"][0].copy())
    rows = receive_payload(payload, NOW)["results"]
    assert rows[0]["reasons"] == ["expired"]
    assert rows[1]["status"] == "invalid"


def test_invalid_envelope():
    """Verify that invalid envelope."""
    with pytest.raises(ValueError):
        receive_payload({"schema_version": True}, NOW)


def test_exporter_contract():
    """Verify that exporter contract."""
    raw = {
        "quests": [
            {
                "config": {
                    "id": "q1",
                    "application": {"id": "a1", "name": "Example"},
                    "starts_at": "2026-10-01T00:00:00Z",
                    "expires_at": "2026-10-10T00:00:00Z",
                    "task_config_v2": {
                        "tasks": {"EXAMPLE_EVENT": {"target": 900}}
                    },
                },
                "user_status": {"enrolled_at": NOW.isoformat()},
                "secret": "must-not-export",
            }
        ]
    }
    payload = normalize_quests(raw, NOW)
    assert "must-not-export" not in str(payload)
    assert (
        receive_payload(payload, NOW)["results"][0]["status"] == "needs_review"
    )
