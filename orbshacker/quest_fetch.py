import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def parse_timestamp(value):
    """Accept timezone-aware ISO timestamps without guessing missing
    timezones.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def get_deadline_status(config, now):
    """Describe the quest time window without guessing missing dates."""
    starts_at = parse_timestamp(config.get("starts_at"))
    expires_at = parse_timestamp(config.get("expires_at"))

    if expires_at is None:
        return "Unknown (missing or invalid expiry)"
    if starts_at is not None and starts_at >= expires_at:
        return "Unknown (start must precede expiry)"
    if now >= expires_at:
        return "Expired"
    if starts_at is None:
        return "Not expired (unknown start)"
    if now < starts_at:
        return "Not started"
    return "Active"


def display_timestamp(value):
    """Format a valid timestamp in UTC, or return an unknown marker."""
    parsed = parse_timestamp(value)
    return parsed.strftime("%Y-%m-%d %H:%M:%S UTC") if parsed else "Unknown"


def normalize_quests(data, now=None):
    """Export an allowlisted transport format; never include credentials."""
    now = now or datetime.now(timezone.utc)
    if not isinstance(data, dict) or not isinstance(data.get("quests"), list):
        raise ValueError("Response must contain a quests array")
    records = []
    for quest in data["quests"]:
        config = quest["config"]
        status = quest.get("user_status") or {}
        application = config.get("application") or {}
        task_config = (
            config.get("task_config_v2") or config.get("task_config") or {}
        )
        progress = status.get("progress") or {}
        tasks = []
        for event, task in (task_config.get("tasks") or {}).items():
            current = progress.get(event) or {}
            tasks.append(
                {
                    "event": event,
                    "target": task.get("target"),
                    "progress": current.get("value"),
                }
            )
        records.append(
            {
                "quest_id": str(config.get("id") or quest.get("id") or ""),
                "application": {
                    "id": str(application.get("id") or ""),
                    "name": application.get("name"),
                },
                "starts_at": config.get("starts_at"),
                "expires_at": config.get("expires_at"),
                "enrolled": bool(
                    status.get("enrolled_at")
                ),  # Enrollment timestamp present
                "completed": bool(
                    status.get("completed_at")
                ),  # Completion timestamp present
                "claimed": bool(
                    status.get("claimed_at")
                ),  # Claim timestamp present
                "task_join_operator": task_config.get("join_operator"),
                "tasks": tasks,
            }
        )
    return {
        "schema_version": 1,
        "fetched_at": now.isoformat(),
        "quests": records,
    }


def display_quests(data):
    """Print active quests and their enrollment and reward states."""
    now = datetime.now(timezone.utc)
    for quest in data["quests"]:
        config = quest["config"]
        status = quest.get("user_status") or {}
        if get_deadline_status(config, now) != "Active":
            continue
        print(f"Quest ID: {config['id']}")
        print(f"Game: {config['application']['name']}")
        print(f"Status: {get_deadline_status(config, now)}")
        print(f"Starts at: {display_timestamp(config.get('starts_at'))}")
        print(f"Expires at: {display_timestamp(config.get('expires_at'))}")
        print(f"Enrolled: {'Yes' if status.get('enrolled_at') else 'No'}")
        print(f"Completed: {'Yes' if status.get('completed_at') else 'No'}")
        print(f"Claimed: {'Yes' if status.get('claimed_at') else 'No'}")
        print()


def retry_delay(response):
    """Respect numeric Retry-After and Discord retry_after, without an
    unbounded wait.
    """
    delays = []
    try:
        body = response.json()
    except ValueError:
        body = {}
    for value in (
        response.headers.get("Retry-After"),
        body.get("retry_after") if isinstance(body, dict) else None,
    ):
        try:
            delay = float(value)
            if math.isfinite(delay) and delay >= 0:
                delays.append(delay)
        except (ValueError, TypeError):
            pass
    return max([1.0, *delays]) if delays else 30.0


def fetch_quests():
    """Read current account state without changing enrollment or rewards."""
    import requests
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    authorization = os.getenv("Authorization")
    if not authorization:
        raise ValueError("Missing Authorization environment variable")
    for attempt in range(3):
        response = requests.get(
            "https://discordapp.com/api/v9/quests/@me",
            headers={
                "Authorization": authorization,
                "User-Agent": "Mozilla/5.0",
            },
            timeout=30,
        )
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()
        delay = retry_delay(response)
        response.close()
        if attempt == 2 or delay > 120:
            raise ValueError(
                f"Discord rate limit (429). Retry after at least {delay:g} "
                "seconds; no more requests sent."
            )
        print(
            f"Discord rate limit (429); waiting {delay:g}s "
            f"before retry {attempt + 1}/2.",
            file=sys.stderr,
            flush=True,
        )
        while delay > 0:
            pause = min(delay, 30)
            time.sleep(pause)
            delay -= pause


def main(argv=None):
    """Display account quests or export normalized JSON."""
    parser = argparse.ArgumentParser(
        description="Display quests or export normalized JSON"
    )
    parser.add_argument(
        "--output", type=Path, help="Write normalized JSON to this file"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Read a saved API response instead of requesting Discord",
    )
    args = parser.parse_args(argv)
    try:
        if args.input:
            data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        else:
            data = fetch_quests()
        if args.output:
            payload = normalize_quests(data)
            args.output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Exported {len(payload['quests'])} quests: {args.output}")
        else:
            display_quests(data)
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        parser.exit(1, f"Export failed: {exc}\n")


if __name__ == "__main__":
    main()
