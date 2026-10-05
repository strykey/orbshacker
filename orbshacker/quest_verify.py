"""Observe server-side desktop progress while trying one candidate at a
time.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .quest_input import receive_payload
from .quest_runner import ROOT, build_plan, running_game


def progress_snapshot(payload, quest_id):
    """Read validated desktop progress for one uniquely identified quest."""
    rows = [q for q in payload["quests"] if q.get("quest_id") == quest_id]
    if len(rows) != 1:
        raise ValueError("Quest missing or duplicated")
    quest = rows[0]
    status = next(
        r
        for r in receive_payload(payload)["results"]
        if r["quest_id"] == quest_id
    )
    if status["status"] == "invalid":
        raise ValueError("Invalid quest data")
    tasks = [t for t in quest["tasks"] if t["event"] == "PLAY_ON_DESKTOP"]
    if len(tasks) != 1:
        raise ValueError("Desktop progress unavailable")
    return {
        "value": tasks[0]["progress"],
        "completed": quest["completed"],
        "eligible": status["status"] == "needs_review",
    }


def observe(row, refresh, work_root, seconds=90, interval=15):
    """Require two numeric increases; null is never silently converted to
    zero.
    """
    baseline = progress_snapshot(refresh(), row["quest_id"])
    result = {
        "executable": row["executable"],
        "status": "inconclusive",
        "samples": [baseline],
    }
    if not baseline["eligible"]:
        result["status"] = "no_longer_eligible"
        return result
    previous, increases = baseline["value"], 0
    with running_game(dict(row, run_seconds=seconds), work_root) as proc:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
            if proc.poll() is not None:
                result["status"] = "process_exited"
                return result
            sample = progress_snapshot(refresh(), row["quest_id"])
            sample["observed_at"] = datetime.now(timezone.utc).isoformat()
            result["samples"].append(sample)
            current = sample["value"]
            if current is not None and previous is not None:
                if current < previous:
                    result["status"] = "progress_reset"
                    return result
                if current > previous:
                    increases += 1
            if current is not None:
                previous = current
            print(
                f"  {row['executable']}: server progress={current}; "
                f"increases={increases}",
                flush=True,
            )
            if increases >= 2:
                result["status"] = "progress_observed"
                return result
            if not sample["eligible"]:
                result["status"] = (
                    "completed_unconfirmed"
                    if sample["completed"]
                    else "no_longer_eligible"
                )
                return result
    return result


def assert_no_conflicts(candidates):
    """Fail closed if process inventory is unavailable. Never terminate
    external processes.
    """
    command = (
        "Get-Process | Select-Object -ExpandProperty ProcessName "
        "| ConvertTo-Json -Compress"
    )
    output = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-Command", command],
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=30,
    )
    names = json.loads(output)
    if isinstance(names, str):
        names = [names]
    names = {n.casefold() for n in names}
    if not any(n.startswith("discord") for n in names):
        raise ValueError("Discord desktop is not running")
    conflicting = {Path(p).stem.casefold() for p in candidates} & names
    if conflicting:
        raise ValueError(
            "Existing game processes would contaminate verification: "
            + ", ".join(sorted(conflicting))
        )


def main(argv=None):
    """Observe selected applications and save evidence under the lock."""
    parser = argparse.ArgumentParser(
        description=(
            "Launch candidates individually and observe real quest progress"
        )
    )
    parser.add_argument("--application-id", action="append", required=True)
    parser.add_argument(
        "--seconds",
        type=int,
        default=90,
        choices=range(60, 301),
        metavar="60..300",
    )
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        parser.error("Windows is required")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    from .discord_db import DiscordGamesDB
    from .quest_fetch import fetch_quests, normalize_quests
    from .quest_runner import runner_lock

    work_root = ROOT / ".quest-runs"
    work_root.mkdir(exist_ok=True)
    report_path = work_root / "verification-report.json"
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
    }

    def save():
        """Persist verification evidence while holding the runner lock."""
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def refresh():
        """Fetch and normalize a fresh account snapshot."""
        return normalize_quests(fetch_quests())

    with runner_lock(work_root):
        try:
            db = DiscordGamesDB()
            plan = build_plan(refresh(), db)
            for row in plan["results"]:
                if (
                    row.get("application", {}).get("id")
                    not in args.application_id
                ):
                    continue
                record = {
                    "quest_id": row["quest_id"],
                    "application": row["application"],
                    "status": row["status"],
                    "attempts": [],
                }
                report["results"].append(record)
                save()
                if row["status"] != "ready":
                    record["reasons"] = row["reasons"]
                    continue
                record["status"] = "inconclusive"
                for executable in row["executable_candidates"]:
                    assert_no_conflicts(row["executable_candidates"])
                    # Quiet interval helps keep delayed updates from the
                    # previous candidate out of baseline.
                    print(
                        f"SETTLING {row['application']['name']}: "
                        f"{executable} (30 seconds)",
                        flush=True,
                    )
                    before = progress_snapshot(refresh(), row["quest_id"])
                    time.sleep(30)
                    after = progress_snapshot(refresh(), row["quest_id"])
                    if before["value"] != after["value"]:
                        record["status"] = "background_progress_detected"
                        break
                    assert_no_conflicts(row["executable_candidates"])
                    result = observe(
                        dict(row, executable=executable),
                        refresh,
                        work_root,
                        args.seconds,
                    )
                    record["attempts"].append(result)
                    save()
                    if result["status"] == "progress_observed":
                        record.update(
                            status="progress_observed",
                            executable=executable,
                            verified_at=datetime.now(timezone.utc).isoformat(),
                        )
                        break
                    if result["status"] in (
                        "no_longer_eligible",
                        "completed_unconfirmed",
                        "progress_reset",
                    ):
                        record["status"] = result["status"]
                        break
                save()
        except KeyboardInterrupt:
            report["error"] = "interrupted"
            return 130
        except Exception as exc:
            report["error"] = str(exc)
            print(f"Verification stopped: {exc}", file=sys.stderr)
            return 1
        finally:
            save()
    return 0
