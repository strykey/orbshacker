from copy import deepcopy

from orbshacker.discord_db import DiscordGamesDB
from orbshacker.quest_runner import build_plan
from tests.test_quest_input import NOW, sample


def fixture():
    """Return a desktop quest and a matching in-memory game database."""
    payload = sample()
    payload["quests"][0]["tasks"][0]["event"] = "PLAY_ON_DESKTOP"
    db = object.__new__(DiscordGamesDB)
    db.games = [
        {
            "id": "example-app",
            "name": "Different display name",
            "executables": [{"os": "win32", "name": "game.exe"}],
        }
    ]
    return payload, db


def test_exact_id_and_unknown_progress():
    """Verify that exact id and unknown progress."""
    payload, db = fixture()
    row = build_plan(payload, db, NOW)["results"][0]
    assert row["status"] == "ready"
    assert row["run_seconds"] == 930
    assert row["database_name"] == "Different display name"


def test_multiple_executables_use_existing_database_selection():
    """Verify that multiple executables use existing database selection."""
    payload, db = fixture()
    db.games[0]["executables"].append({"os": "win32", "name": "other.exe"})
    row = build_plan(payload, db, NOW)["results"][0]
    assert row["status"] == "ready"
    assert (
        row["executable"] == db.get_win32_executable(db.games[0]) == "game.exe"
    )
    assert row["executable_candidates"] == ["game.exe", "other.exe"]
    assert row["selection_policy"] == "first_filtered_database_candidate"
    db.games[0]["id"] = "wrong-id"
    assert build_plan(payload, db, NOW)["results"][0]["status"] == "skipped"


def test_helpers_and_other_platforms_are_not_selected():
    """Verify that helpers and other platforms are not selected."""
    payload, db = fixture()
    db.games[0]["executables"] = [
        {"os": "win32", "name": "launcher.exe"},
        {"os": "linux", "name": "game"},
        {"os": "win32", "name": "crashreport.exe"},
        {"os": "win32", "name": ">actual.exe"},
        {"os": "win32", "name": "alternative.exe"},
    ]
    row = build_plan(payload, db, NOW)["results"][0]
    assert row["executable"] == "actual.exe"
    assert row["executable_candidates"] == ["actual.exe", "alternative.exe"]
    db.games[0]["executables"] = db.games[0]["executables"][:3]
    row = build_plan(payload, db, NOW)["results"][0]
    assert row["status"] == "skipped"
    assert row["reasons"] == ["windows_executable_missing"]


def test_empty_database_executables_still_skipped():
    """Verify that empty database executables still skipped."""
    payload, db = fixture()
    db.games[0]["executables"] = []
    assert build_plan(payload, db, NOW)["results"][0]["reasons"] == [
        "windows_executable_missing"
    ]


def test_or_console_alternative_and_unsupported_and():
    """Verify that or console alternative and unsupported and."""
    payload, db = fixture()
    quest = payload["quests"][0]
    quest["tasks"].append(
        {"event": "PLAY_ON_XBOX", "target": 900, "progress": None}
    )
    quest["task_join_operator"] = "or"
    assert build_plan(payload, db, NOW)["results"][0]["status"] == "ready"
    quest["task_join_operator"] = "and"
    assert build_plan(payload, db, NOW)["results"][0]["status"] == "skipped"


def test_duplicates_block_all_copies():
    """Verify that duplicates block all copies."""
    payload, db = fixture()
    payload["quests"].append(deepcopy(payload["quests"][0]))
    assert all(
        r["status"] != "ready" for r in build_plan(payload, db, NOW)["results"]
    )


def test_completed_progress_and_expiry():
    """Verify that completed progress and expiry."""
    payload, db = fixture()
    payload["quests"][0]["tasks"][0]["progress"] = 900
    assert build_plan(payload, db, NOW)["results"][0]["status"] == "skipped"
    payload["quests"][0]["tasks"][0]["progress"] = 0
    payload["quests"][0]["expires_at"] = "2026-10-03T00:01:00Z"
    assert build_plan(payload, db, NOW)["results"][0]["status"] == "skipped"
