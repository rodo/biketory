# Procrastinate queues

This document lists all procrastinate queues and tasks used in the project.
**It must be updated** whenever a queue or task is added, modified, or removed.

## Workers

Each queue can have its own worker:

```bash
python manage.py procrastinate worker -q surface_extraction
python manage.py procrastinate worker -q badges
```

Or a single worker listening on both queues:

```bash
python manage.py procrastinate worker -q surface_extraction,badges
```

## Queues

| Queue | Description |
|---|---|
| `surface_extraction` | Extract closed surfaces from uploaded traces |
| `badges` | Award badges after surface extraction |

## Tasks

| Task | Queue | Queueing lock | Description |
|---|---|---|---|
| `extract_surfaces` | `surface_extraction` | `extract_surfaces_{trace_id}` | Extract closed surfaces from a trace and set status to `surface_extracted`. |
| `award_trace_badges` | `badges` | `award_badges_{trace_id}` | Award badges for a trace and set status to `analyzed`. Reschedules itself (5s delay) if the trace is not yet `surface_extracted`. |

## Trace lifecycle

`not_analyzed` → `surface_extracted` → `analyzed`

## How it works

1. When a user uploads a trace, `upload.py` defers both `extract_surfaces` and `award_trace_badges` in parallel.
2. `extract_surfaces` runs first, calls `_extract_surfaces()`, then sets `status = "surface_extracted"`.
3. `award_trace_badges` checks the trace status. If not yet `surface_extracted`, it reschedules itself after 5 seconds. Otherwise it calls `award_badges()` then sets `status = "analyzed"`.
4. The trace detail page polls `/api/traces/<uuid>/status/` every 5 seconds and reloads when the status changes (both intermediate and final transitions).

## Catch-up command

If traces are stuck in `not_analyzed` or `surface_extracted` (e.g., worker was down), run:

```bash
python manage.py analyze_traces
```

This defers the appropriate jobs:
- `not_analyzed` traces → `extract_surfaces` + `award_trace_badges`
- `surface_extracted` traces → `award_trace_badges` only
