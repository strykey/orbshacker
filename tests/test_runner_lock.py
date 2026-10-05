import sys

import pytest

from orbshacker import cli, quest_runner


@pytest.mark.skipif(sys.platform != "win32", reason="Windows byte-range lock")
def test_busy_lock_and_release_after_exception(tmp_path):
    """Verify that busy lock and release after exception."""
    with pytest.raises(ValueError):
        with quest_runner.runner_lock(tmp_path):
            with pytest.raises(quest_runner.RunnerBusyError):
                with quest_runner.runner_lock(tmp_path):
                    pytest.fail("Concurrent runner acquired the lock")
            raise ValueError("simulated interruption")
    with quest_runner.runner_lock(tmp_path):
        pass


def test_cli_lock_conflict_is_a_short_message(monkeypatch, capsys):
    """Verify that cli lock conflict is a short message."""

    def busy(args):
        """Simulate an already active runner."""
        raise quest_runner.RunnerBusyError("Another runner is active")

    monkeypatch.setattr(quest_runner, "main", busy)
    assert cli.main(["auto", "--execute"]) == 2
    output = capsys.readouterr()
    assert "Another runner is active" in output.err
    assert "Traceback" not in output.err
