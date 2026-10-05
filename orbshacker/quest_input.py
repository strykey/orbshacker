"""Offline JSON intake. This module never launches processes or requests
APIs.
"""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def _timestamp(value):
    """Parse a required timezone-aware ISO timestamp."""
    if not isinstance(value, str):
        raise ValueError("Expected a timezone-aware timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp requires a timezone")
    return parsed


def receive_payload(payload, now=None):
    """Validate schema v1 and return per-quest intake decisions, not
    execution approval.
    """
    now = now or datetime.now(timezone.utc)
    if (
        not isinstance(payload, dict)
        or type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
    ):
        raise ValueError("Unsupported schema_version; expected 1")
    _timestamp(payload.get("fetched_at"))
    if not isinstance(payload.get("quests"), list):
        raise ValueError("quests must be an array")
    results, seen = [], set()
    for quest in payload["quests"]:
        reasons = []
        if not isinstance(quest, dict):
            results.append(
                {
                    "quest_id": None,
                    "status": "invalid",
                    "reasons": ["quest must be an object"],
                }
            )
            continue
        quest_id = quest.get("quest_id")
        try:
            if not isinstance(quest_id, str) or not quest_id.strip():
                raise ValueError("quest_id must be a nonempty string")
            if quest_id in seen:
                raise ValueError("duplicate quest_id")
            seen.add(quest_id)
            app = quest.get("application")
            if (
                not isinstance(app, dict)
                or not isinstance(app.get("id"), str)
                or not app["id"].strip()
            ):
                raise ValueError("application.id is required")
            if not isinstance(app.get("name"), str) or not app["name"].strip():
                raise ValueError("application.name is required")
            for key in ("enrolled", "completed", "claimed"):
                if type(quest.get(key)) is not bool:
                    raise ValueError(f"{key} must be boolean")
            start, end = (
                _timestamp(quest.get("starts_at")),
                _timestamp(quest.get("expires_at")),
            )
            if start >= end:
                raise ValueError("starts_at must precede expires_at")
            tasks = quest.get("tasks")
            if not isinstance(tasks, list) or not tasks:
                raise ValueError("tasks must be a nonempty array")
            for task in tasks:
                if (
                    not isinstance(task, dict)
                    or not isinstance(task.get("event"), str)
                    or not task["event"].strip()
                ):
                    raise ValueError("task event is required")
                for key in ("target", "progress"):
                    value = task.get(key)
                    if key == "progress" and value is None:
                        # Unknown progress is not an observed zero.
                        continue
                    if (
                        type(value) not in (int, float)
                        or not math.isfinite(value)
                        or value < 0
                        or (key == "target" and value == 0)
                    ):
                        raise ValueError(f"Invalid task {key}")
            if now < start:
                reasons.append("not_started")
            if now >= end:
                reasons.append("expired")
            if not quest["enrolled"]:
                reasons.append("not_enrolled")
            if quest["completed"] or quest["claimed"]:
                reasons.append("already_completed_or_claimed")
            results.append(
                {
                    "quest_id": quest_id,
                    "application": app,
                    "status": "skipped" if reasons else "needs_review",
                    "reasons": reasons
                    or ["task_semantics_and_executable_mapping_not_verified"],
                    "tasks": tasks,
                    "task_join_operator": quest.get("task_join_operator"),
                }
            )
        except (ValueError, TypeError, OverflowError) as exc:
            results.append(
                {
                    "quest_id": quest_id,
                    "status": "invalid",
                    "reasons": [str(exc)],
                }
            )
    return {"schema_version": 1, "mode": "validate_only", "results": results}


def main(argv=None):
    """Validate a JSON file and return the intake exit code."""
    parser = argparse.ArgumentParser(
        description="Validate a normalized quest JSON file; no execution"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = receive_payload(
            json.loads(args.input.read_text(encoding="utf-8-sig"))
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered)
        return (
            2
            if any(row["status"] == "invalid" for row in report["results"])
            else 0
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Import failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
