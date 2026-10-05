"""Match current desktop quests and supervise a bounded local process run."""

import argparse
import json
import math
import sys
import tempfile
import time
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .quest_input import _timestamp, receive_payload

ROOT = Path(__file__).resolve().parents[1]


class RunnerBusyError(RuntimeError):
    """The shared execution lock could not be acquired."""


@contextmanager
def runner_lock(work_root):
    """Hold the shared Windows runner lock until the context exits."""
    with (work_root / "runner.lock").open("a+b") as lock:
        if sys.platform == "win32":
            import msvcrt

            try:
                if lock.seek(0, 2) == 0:
                    lock.write(b"0")
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RunnerBusyError(
                    "Another auto/verify runner is active, "
                    "or runner.lock cannot be accessed. "
                    "Stop the existing runner with Ctrl+C and retry; "
                    "do not delete its lock file."
                ) from exc
        try:
            yield
        finally:
            if sys.platform == "win32":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def apply_verified_choices(plan, work_root):
    """Prefer recorded evidence only for matching current candidates."""
    path = work_root / "verification-report.json"
    if not path.exists():
        return plan
    try:
        results = json.loads(path.read_text(encoding="utf-8"))["results"]
        for row in plan["results"]:
            if row["status"] != "ready":
                continue
            for result in results:
                if (
                    result.get("status") == "progress_observed"
                    and result.get("quest_id") == row["quest_id"]
                    and result.get("application", {}).get("id")
                    == row["application"]["id"]
                    and result.get("executable")
                    in row["executable_candidates"]
                ):
                    row.update(
                        executable=result["executable"],
                        selection_policy="previously_observed_server_progress",
                    )
    except (ValueError, KeyError, TypeError, AttributeError):
        pass  # Invalid evidence must not create an executable path.
    return plan


def build_plan(payload, db, now=None):
    """Match eligible desktop quests to bounded executable plans."""
    now = now or datetime.now(timezone.utc)
    report = receive_payload(payload, now)
    quests = {
        q["quest_id"]: q
        for q in payload["quests"]
        if isinstance(q, dict) and isinstance(q.get("quest_id"), str)
    }
    duplicate_ids = {
        row["quest_id"]
        for row in report["results"]
        if "duplicate quest_id" in row["reasons"]
    }
    for row in report["results"]:
        if row["status"] != "needs_review":
            continue
        row["status"] = "skipped"
        row["reasons"] = []
        quest = quests[row["quest_id"]]
        desktop = [t for t in row["tasks"] if t["event"] == "PLAY_ON_DESKTOP"]
        if row["quest_id"] in duplicate_ids:
            row["reasons"] = ["duplicate quest_id"]
        elif len(desktop) != 1 or (
            len(row["tasks"]) > 1 and row["task_join_operator"] != "or"
        ):
            row["reasons"] = ["unsupported_task_conditions"]
        else:
            task = desktop[0]
            remaining = (
                task["target"]
                if task["progress"] is None
                else task["target"] - task["progress"]
            )
            matches = [
                g
                for g in db.games
                if str(g.get("id")) == row["application"]["id"]
            ]
            if remaining <= 0:
                row["reasons"] = ["target_reached_wait_for_server"]
            elif remaining > 7200:
                row["reasons"] = ["duration_exceeds_two_hour_limit"]
            elif (
                _timestamp(quest["expires_at"]) - now
            ).total_seconds() < remaining + 30:
                row["reasons"] = ["insufficient_time_before_expiry"]
            elif len(matches) != 1:
                row["reasons"] = [
                    "application_id_not_unique_or_missing_in_database"
                ]
            else:
                exes = db._filter_win32_exes(matches[0], skip_patterns=True)
                selected = db.get_win32_executable(matches[0])
                row["executable_candidates"] = exes
                if selected is None:
                    row["reasons"] = ["windows_executable_missing"]
                else:
                    row.update(
                        status="ready",
                        executable=selected,
                        selection_policy="first_filtered_database_candidate",
                        database_name=matches[0].get("name"),
                        run_seconds=math.ceil(remaining) + 30,
                        expires_at=quest["expires_at"],
                    )
    report["mode"] = "plan"
    return report


@contextmanager
def running_game(row, work_root):
    """Launch an isolated process and clean it up on context exit."""
    from . import config
    from .faker import GameFaker

    # Temporary, per-run output never overwrites a real game or a previous run.
    with tempfile.TemporaryDirectory(prefix="quest-", dir=work_root) as folder:
        faker = GameFaker()
        faker.chosen_path = Path(folder)
        old_delete, old_minutes, old_manifest = (
            config.AUTO_DELETE,
            config.TIMER_MINUTES,
            config.STEAM_MANIFEST_PATH,
        )
        try:
            # The supervisor owns shutdown; do not bake shell self-deletion
            # into copies.
            config.AUTO_DELETE = False
            config.STEAM_MANIFEST_PATH = None
            config.TIMER_MINUTES = math.ceil(row["run_seconds"] / 60)
            path = faker.create_fake_game(row["executable"])
            if path is None or not faker.launch_executable(path):
                raise RuntimeError("Process creation or launch failed")
            (
                config.AUTO_DELETE,
                config.TIMER_MINUTES,
                config.STEAM_MANIFEST_PATH,
            ) = old_delete, old_minutes, old_manifest
            proc = faker._processes[-1]
            if proc.poll() is not None:
                raise RuntimeError("Process exited immediately")
            print(
                f"RUNNING {row['application']['name']} pid={proc.pid} "
                f"seconds={row['run_seconds']}",
                flush=True,
            )
            yield proc
        finally:
            for proc in faker._processes:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()
                        proc.wait(timeout=5)
            (
                config.AUTO_DELETE,
                config.TIMER_MINUTES,
                config.STEAM_MANIFEST_PATH,
            ) = old_delete, old_minutes, old_manifest


def run_batch(plan, db, work_root, refresh, save):
    """Launch all eligible games, then supervise each independent lifetime."""
    payload = (
        refresh()
    )  # One snapshot for the batch; recheck time locally before each launch.
    active = []
    with ExitStack() as all_games:
        try:
            for row in plan["results"]:
                if row["status"] != "ready":
                    continue
                fresh_plan = build_plan(payload, db)
                current = next(
                    (
                        item
                        for item in fresh_plan["results"]
                        if item["quest_id"] == row["quest_id"]
                    ),
                    None,
                )
                if current is None or current["status"] != "ready":
                    row.update(
                        status="skipped",
                        reasons=(
                            current["reasons"]
                            if current
                            else ["quest_missing_before_launch"]
                        ),
                    )
                    save()
                    continue
                try:
                    owned = ExitStack()
                    all_games.callback(owned.close)
                    proc = owned.enter_context(running_game(row, work_root))
                    row.update(status="running", pid=proc.pid)
                    active.append(
                        (
                            row,
                            proc,
                            time.monotonic() + row["run_seconds"],
                            owned,
                        )
                    )
                except Exception as exc:
                    row.update(status="failed", reasons=[str(exc)])
                save()

            while active:
                for item in active[:]:
                    row, proc, deadline, owned = item
                    if proc.poll() is not None:
                        row.update(
                            status="failed",
                            reasons=["Process exited before the run finished"],
                        )
                    elif datetime.now(timezone.utc) >= _timestamp(
                        row["expires_at"]
                    ):
                        row.update(
                            status="expired", reasons=["expired_during_run"]
                        )
                    elif time.monotonic() >= deadline:
                        row["status"] = "run_finished_unverified"
                    else:
                        continue
                    try:
                        owned.close()
                    except Exception as exc:
                        row.update(
                            status="failed", reasons=[f"Cleanup failed: {exc}"]
                        )
                    active.remove(item)
                    save()
                if active:
                    time.sleep(1)
        finally:
            for row, _, _, _ in active:
                if row["status"] == "running":
                    row.update(
                        status="interrupted", reasons=["runner_stopped"]
                    )
            all_games.close()
            save()


def main(argv=None):
    """Preview or execute a batch and write its status report."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description=(
            "Fetch and match current desktop quests; default is preview only"
        )
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.execute and sys.platform != "win32":
        parser.error("Execution requires Windows")
    from .discord_db import DiscordGamesDB
    from .quest_fetch import fetch_quests, normalize_quests

    work_root = ROOT / ".quest-runs"
    work_root.mkdir(exist_ok=True)
    # OS lock releases on crash; retain the lock file so other processes share
    # its identity.
    with runner_lock(work_root):
        db = DiscordGamesDB()
        payload = normalize_quests(fetch_quests())
        plan = apply_verified_choices(build_plan(payload, db), work_root)
        report_path = work_root / "latest-report.json"
        report_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for row in plan["results"]:
            name = row.get("application", {}).get("name", row["quest_id"])
            print(
                f"{row['status']}: {name}: "
                f"{row.get('executable') or ', '.join(row['reasons'])}",
                flush=True,
            )
            if len(row.get("executable_candidates", [])) > 1:
                print(
                    f"  Selection: {row['selection_policy']}; alternatives: "
                    + ", ".join(
                        x
                        for x in row["executable_candidates"]
                        if x != row["executable"]
                    ),
                    flush=True,
                )
        if not args.execute:
            return 0

        def save():
            """Persist the latest batch state to the local report."""
            report_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        try:
            run_batch(plan, db, work_root, lambda: payload, save)
        except KeyboardInterrupt:
            print("Stopped; launched processes have been cleaned up.")
            return 130
        return (
            1 if any(r["status"] == "failed" for r in plan["results"]) else 0
        )


if __name__ == "__main__":
    raise SystemExit(main())
