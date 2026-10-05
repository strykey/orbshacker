from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest

from orbshacker import quest_runner as runner


def setup_batch(monkeypatch, fail=None, interrupt=False):
    """Install a fake clock and processes for deterministic batch tests."""
    rows = [
        {
            "quest_id": name,
            "status": "ready",
            "run_seconds": seconds,
            "expires_at": "2099-01-01T00:00:00Z",
        }
        for name, seconds in [("short", 1), ("long", 3)]
    ]
    plan = {"results": rows}
    fresh = deepcopy(plan)
    clock = [0]
    live = set()
    events = []

    @contextmanager
    def game(row, root):
        """Yield a fake process and record cleanup when its context exits."""
        name = row["quest_id"]
        if name == fail:
            raise RuntimeError("launch failed")
        live.add(name)
        events.append(("start", name, set(live)))
        try:
            yield SimpleNamespace(pid=len(events), poll=lambda: None)
        finally:
            live.remove(name)
            events.append(("stop", name, set(live)))

    def sleep(seconds):
        """Advance the fake clock or simulate a user interruption."""
        if interrupt:
            raise KeyboardInterrupt
        clock[0] += seconds

    monkeypatch.setattr(runner, "running_game", game)
    monkeypatch.setattr(
        runner, "build_plan", lambda payload, db: deepcopy(fresh)
    )
    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(runner.time, "sleep", sleep)
    return plan, live, events


def test_games_overlap_and_finish_independently(monkeypatch, tmp_path):
    """Verify that games overlap and finish independently."""
    plan, live, events = setup_batch(monkeypatch)
    calls = []

    def refresh():
        """Record a snapshot request and return the fake payload."""
        calls.append(True)
        return {}

    runner.run_batch(plan, None, tmp_path, refresh, lambda: None)
    assert calls == [True]
    assert events == [
        ("start", "short", {"short"}),
        ("start", "long", {"short", "long"}),
        ("stop", "short", {"long"}),
        ("stop", "long", set()),
    ]
    assert not live
    assert all(
        r["status"] == "run_finished_unverified" for r in plan["results"]
    )


def test_failed_launch_does_not_stop_other_game(monkeypatch, tmp_path):
    """Verify that failed launch does not stop other game."""
    plan, live, events = setup_batch(monkeypatch, fail="long")
    runner.run_batch(plan, None, tmp_path, lambda: {}, lambda: None)
    assert plan["results"][0]["status"] == "run_finished_unverified"
    assert plan["results"][1]["status"] == "failed"
    assert not live


def test_interrupt_closes_all_games(monkeypatch, tmp_path):
    """Verify that interrupt closes all games."""
    plan, live, events = setup_batch(monkeypatch, interrupt=True)
    with pytest.raises(KeyboardInterrupt):
        runner.run_batch(plan, None, tmp_path, lambda: {}, lambda: None)
    assert not live
    assert all(r["status"] == "interrupted" for r in plan["results"])


def test_expired_quest_is_skipped_before_launch(monkeypatch, tmp_path):
    """Verify that expired quest is skipped before launch."""
    plan, live, events = setup_batch(monkeypatch)
    fresh = deepcopy(plan)
    fresh["results"][0].update(status="skipped", reasons=["expired"])
    monkeypatch.setattr(runner, "build_plan", lambda payload, db: fresh)
    runner.run_batch(plan, None, tmp_path, lambda: {}, lambda: None)
    assert plan["results"][0]["status"] == "skipped"
    assert plan["results"][0]["reasons"] == ["expired"]
    assert not any(
        event[0] == "start" and event[1] == "short" for event in events
    )
    assert plan["results"][1]["status"] == "run_finished_unverified"
    assert not live
