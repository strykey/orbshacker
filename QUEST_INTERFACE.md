# Quest JSON Interface v1

This document describes normalized quest JSON and offline validation. Intake
does not launch processes, make network requests, enroll in quests, or claim
rewards. Fetching current account data requires network access and local
authorization configuration. The example data is fictional.

See [Quest workflow](docs/QUEST_WORKFLOW.md) for setup and execution commands.

## Usage

Run commands from the repository root:

```powershell
# Fetch current account data using local authorization configuration.
python -m orbshacker fetch --output quests.json

# Convert a saved API response without network access.
python -m orbshacker fetch --input raw-response.json --output quests.json

# Validate normalized JSON without network access or process execution.
python -m orbshacker intake quests.json --output intake-report.json
python -m orbshacker intake examples/quests.example.json
```

The Python interface returns the same report dictionary as the intake CLI:

```python
from orbshacker.quest_input import receive_payload

report = receive_payload(payload)
```

## Data contract

The root object contains integer `schema_version: 1`, a timezone-aware ISO
timestamp `fetched_at`, and a `quests` array. Each quest contains:

| Field | Meaning |
| --- | --- |
| `quest_id` | Nonempty string; must be unique within the batch |
| `application.id`, `application.name` | Nonempty application ID and name strings |
| `starts_at`, `expires_at` | Timezone-aware ISO timestamps; start must precede expiry |
| `enrolled`, `completed`, `claimed` | Booleans derived from the presence of the corresponding source timestamps |
| `task_join_operator` | Source condition operator; missing values are represented as `null` |
| `tasks` | Nonempty array of objects containing `event`, `target`, and `progress` |

`event` preserves the source event name. `target` must be a finite positive
number; `progress` must be a finite nonnegative number or `null` (unknown).
Unknown progress is never interpreted as an observed zero.

The exporter prefers `task_config_v2`, falling back to `task_config`. It exports
selected fields rather than the full response and excludes Authorization.
Intake does not establish event semantics or units: values must not universally
be interpreted as seconds. The desktop runner applies its own narrower rules.

## Intake results

- `needs_review`: Valid data for an enrolled, unfinished quest within its time
  window. Task semantics and executable mapping still require review.
- `skipped`: Not started, expired, not enrolled, completed, or claimed.
- `invalid`: Invalid fields, missing required information, or a repeated quest ID.

An invalid item is reported while other items continue to be checked. For
duplicate IDs, intake marks subsequent occurrences invalid; the runner blocks
all occurrences of the duplicated ID.

| Intake exit code | Meaning |
| --- | --- |
| `0` | Validation finished with no invalid items; not execution approval or completion evidence |
| `1` | File error or invalid root structure |
| `2` | At least one invalid item |

Time windows are checked at intake time. Saved reports do not establish current
server progress. There is no persistent queue, cross-batch deduplication, or
HTTP service. Keep account exports and reports out of version control.
