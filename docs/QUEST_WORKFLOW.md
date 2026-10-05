# Additional Quest Workflow

This guide covers the added quest commands. The original interactive menu,
Steam mode, author attribution, and upstream documentation remain available.
The commands do not depend on a neighboring checkout or backup folder.

## Setup

Execution and candidate verification require Windows. The existing release
workflow uses Python 3.12; the upstream Python 3.7 badge should not be treated
as a verified minimum for this extension. Run these commands from the repository
root in an environment with the dependencies installed:

```powershell
python -m pip install -r requirements.txt
python -m orbshacker --help
```

For online commands, create `.env` from `.env.example` only if `.env` does not
already exist, then fill in `Authorization` locally. An existing environment
variable takes precedence over `.env`. Do not commit credentials or account
exports. Offline conversion and intake do not require authorization.

## Commands

```powershell
# Fetch and export normalized account data.
python -m orbshacker fetch --output quests.json

# Convert a saved API response offline.
python -m orbshacker fetch --input raw-response.json --output quests.json

# Validate without launching processes or contacting the API.
python -m orbshacker intake quests.json --output intake-report.json
python -m orbshacker intake examples/quests.example.json

# Fetch and preview matches; writes a report but launches no game processes.
python -m orbshacker auto

# Execute eligible desktop matches.
python -m orbshacker auto --execute

# Observe candidates for an application ID from the quest export.
python -m orbshacker verify --application-id APPLICATION_ID --seconds 90

# Open the original interactive menu.
python -m orbshacker menu
```

Replace `APPLICATION_ID` with the actual application ID. `--application-id`
may be repeated. Verification accepts `--seconds` from 60 through 300, with a
default of 90 seconds per candidate, plus settling and request time.

`python -m orbshacker` without arguments still opens the menu.
`python orbshacker.py` supports the same commands, and `python fetch.py` remains
a compatibility entry point for fetching. Each subcommand supports `--help`.

## Execution behavior

The runner requires an enrolled, unfinished, unclaimed quest within its time
window and exactly one independently satisfiable `PLAY_ON_DESKTOP` condition.
When multiple task conditions exist, only the `or` operator is supported.
Applications are matched by exact ID, not by display name.

Windows executable selection uses the existing database filtering and ordering.
Previously observed progress can prioritize a candidate only when the quest ID,
application ID, and current candidate list still match. No suitable executable
means the quest is skipped; there is no automatic Steam fallback.

The runner treats desktop target and progress values as seconds. Its budget is
the remaining target rounded up, plus a 30-second buffer. Unknown progress uses
the full target as a budget, not as evidence of zero progress. Remaining targets
over two hours are skipped; accepted budgets can include another 30 seconds.
Quests without enough time before expiry are skipped.

One account snapshot is shared across the batch. Local time and eligibility
are rechecked before each launch; `auto --execute` does not poll live progress.
Processes start sequentially and then run concurrently, each with its own
temporary directory, PID, and deadline. One launch failure does not stop the
others. Ctrl+C cleans up processes launched by this batch. Forced termination
may leave processes or temporary files behind.

Keep Discord desktop running. Multiple local processes do not establish that
Discord credits multiple quests simultaneously. `run_finished_unverified` means
only that the local budget ended; it does not mean the quest completed.
The commands do not enroll in quests or automatically claim rewards.

## Candidate verification

`verify` tests candidates individually. Before each candidate, it checks for
conflicting game processes and waits through a 30-second settling period.
Changing progress during that period stops the check for that quest. External
processes are never terminated by verification.

During observation, the command samples desktop progress approximately every
15 seconds and requires two numeric increases for `progress_observed`. Unknown
values remain unknown. No increase within the window is `inconclusive`, not
proof that the filename is wrong. API delays may affect timing and attribution.
Evidence describes that observation and does not guarantee future recognition.

Both online modes respect numeric server retry delays for HTTP 429, retry at
most twice, and stop if a requested delay exceeds 120 seconds.

## Reports and local files

| Path | Purpose and retention |
| --- | --- |
| `.env` | Local authorization; preserve locally and do not commit |
| `quests.json` | Saved account snapshot; removable when no longer needed |
| `intake-report.json` | Offline validation report; removable when no longer needed |
| `.quest-runs/latest-report.json` | Latest auto plan/execution report; overwritten by subsequent auto runs |
| `.quest-runs/verification-report.json` | Latest verification evidence; later auto runs can use it to select candidates |
| `.quest-runs/runner.lock` | Shared Windows auto/verify lock; do not delete to bypass a running command |
| `.quest-runs/quest-*` | Temporary per-process directories, normally cleaned on exit |

Verification replaces its report after acquiring the shared lock; new runs do
not merge older evidence. A rejected concurrent verification does not overwrite
the existing report. The lock does not cover the original menu or other tools.
Do not clear runtime files while a runner is active. Python and pytest caches
can be regenerated; deleting the virtual environment requires reinstalling
dependencies.

## Development and tests

| Module | Responsibility |
| --- | --- |
| `orbshacker/cli.py` | Command dispatch and compatibility with the original menu |
| `orbshacker/quest_fetch.py` | Account reads, display, normalization, and rate-limit handling |
| `orbshacker/quest_input.py` | Offline schema and eligibility validation |
| `orbshacker/quest_runner.py` | Matching, shared lock, process lifetime, and reports |
| `orbshacker/quest_verify.py` | Candidate observation and progress evidence |

```powershell
python -m pytest -q
```

The quest tests use fixtures and mocked network/process operations. They do not
prove live Discord recognition. `examples/quests.example.json` contains fictional
data; its time-dependent intake result may change as the dates pass. See the
[JSON interface](../QUEST_INTERFACE.md) and the original
[contribution guidelines](../CONTRIBUTING.md).

The existing compiled-app updater still targets the upstream release repository.
A custom build should review that configuration before distribution, since an
upstream update may not contain these additions. Source execution does not run
the compiled-app updater. Compiled support for these commands requires separate
packaging verification.
