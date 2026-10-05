import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_offline_export_and_intake(tmp_path):
    """Verify that offline export and intake."""
    raw = tmp_path / "raw.json"
    exported = tmp_path / "quests.json"
    report = tmp_path / "report.json"
    raw.write_text(
        json.dumps(
            {
                "quests": [
                    {
                        "config": {
                            "id": "q1",
                            "application": {"id": "a1", "name": "Example"},
                            "starts_at": "2020-01-01T00:00:00Z",
                            "expires_at": "2020-01-02T00:00:00Z",
                            "task_config": {
                                "tasks": {"EXAMPLE_EVENT": {"target": 1}}
                            },
                        },
                        "user_status": {"enrolled_at": "2020-01-01T00:00:00Z"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "orbshacker",
            "fetch",
            "--input",
            str(raw),
            "--output",
            str(exported),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "orbshacker",
            "intake",
            str(exported),
            "--output",
            str(report),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    assert json.loads(report.read_text(encoding="utf-8"))["results"][0][
        "reasons"
    ] == ["expired"]


def test_legacy_entries_and_unknown_command():
    """Verify that legacy entries and unknown command."""
    for entry in (["fetch.py"], ["orbshacker.py"], ["-m", "orbshacker"]):
        result = subprocess.run(
            [sys.executable, *entry, "--help"], cwd=ROOT, capture_output=True
        )
        assert result.returncode == 0
    result = subprocess.run(
        [sys.executable, "-m", "orbshacker", "unknown"],
        cwd=ROOT,
        capture_output=True,
    )
    assert result.returncode == 2
