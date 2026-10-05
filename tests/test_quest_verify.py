import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from orbshacker import quest_verify as verify
from orbshacker.quest_runner import apply_verified_choices


def test_busy_verification_preserves_existing_report(monkeypatch, tmp_path):
    """Verify that busy verification preserves existing report."""
    from orbshacker import cli, quest_runner

    work_root = tmp_path / ".quest-runs"
    work_root.mkdir()
    report = work_root / "verification-report.json"
    original = '{"results": [{"status": "progress_observed"}]}'
    report.write_text(original, encoding="utf-8")

    @contextmanager
    def busy_lock(root):
        """Simulate lock contention before verification can write a report."""
        raise quest_runner.RunnerBusyError("Another runner is active")
        yield

    monkeypatch.setattr(verify, "ROOT", tmp_path)
    monkeypatch.setattr(verify.sys, "platform", "win32")
    monkeypatch.setattr(quest_runner, "runner_lock", busy_lock)
    assert cli.main(["verify", "--application-id", "example"]) == 2
    assert report.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "values,status",
    [
        ([None, 10, 20, 30], "progress_observed"),
        ([0, 10, 10, 10], "inconclusive"),
        ([None, None, None, None], "inconclusive"),
        ([10, 5], "progress_reset"),
    ],
)
def test_requires_repeated_numeric_progress(
    monkeypatch, tmp_path, values, status
):
    """Verify that requires repeated numeric progress."""
    clock = [0]
    samples = iter(values)
    closed = []
    monkeypatch.setattr(
        verify,
        "progress_snapshot",
        lambda *a: {
            "value": next(samples),
            "eligible": True,
            "completed": False,
        },
    )
    monkeypatch.setattr(verify.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        verify.time, "sleep", lambda n: clock.__setitem__(0, clock[0] + n)
    )

    @contextmanager
    def game(*args):
        """Yield a fake process and record cleanup when its context exits."""
        try:
            yield SimpleNamespace(poll=lambda: None)
        finally:
            closed.append(True)

    monkeypatch.setattr(verify, "running_game", game)
    result = verify.observe(
        {"quest_id": "q", "executable": "game.exe"}, lambda: {}, tmp_path, 45
    )
    assert result["status"] == status
    assert closed == [True]


def test_evidence_must_match_quest_and_database_candidate(tmp_path):
    """Verify that evidence must match quest and database candidate."""
    row = {
        "quest_id": "q",
        "application": {"id": "app"},
        "status": "ready",
        "executable": "a.exe",
        "executable_candidates": ["a.exe", "b.exe"],
    }
    record = {
        "quest_id": "q",
        "application": {"id": "app"},
        "status": "progress_observed",
        "executable": "b.exe",
    }
    path = tmp_path / "verification-report.json"
    path.write_text(json.dumps({"results": [record]}))
    apply_verified_choices({"results": [row]}, tmp_path)
    assert row["executable"] == "b.exe"
    record["executable"] = "untrusted.exe"
    path.write_text(json.dumps({"results": [record]}))
    apply_verified_choices({"results": [row]}, tmp_path)
    assert row["executable"] == "b.exe"
