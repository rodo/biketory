# Procrastinate queues

This document lists all procrastinate queues and tasks used in the project.
**It must be updated** whenever a queue or task is added, modified, or removed.

## Workers

Each queue can have its own worker:

```bash
python manage.py procrastinate worker -q surface_extraction
python manage.py procrastinate worker -q badges
python manage.py procrastinate worker -q tiles
```

Or a single worker listening on all queues:

```bash
python manage.py procrastinate worker -q surface_extraction,badges,tiles
```

## Queues

| Queue | Description |
|---|---|
| `surface_extraction` | Extract closed surfaces from uploaded traces |
| `badges` | Award badges after surface extraction |
| `tiles` | Generate hexagon PNG tiles for a trace's bounding box |

## Tasks

| Task | Queue | Queueing lock | Description |
|---|---|---|---|
| `extract_surfaces` | `surface_extraction` | `extract_surfaces_<trace_id>` (set at defer time) | Extract closed surfaces from a trace and set status to `surface_extracted`. |
| `award_trace_badges` | `badges` | `award_badges_<trace_id>` (set at defer time) | Award badges for a trace and set status to `analyzed`. Reschedules itself (5s delay) if the trace is not yet `surface_extracted`. |
| `generate_tiles` | `tiles` | `generate_tiles_<trace_id>_<zoom>` (set at defer time) | Generate hexagon PNG tiles for a trace's bbox at a given zoom level. Reschedules itself (5s delay) if the trace is still `not_analyzed`. |

## Trace lifecycle

`not_analyzed` → `surface_extracted` → `analyzed`

## How it works

1. When a user uploads a trace, `upload.py` defers `extract_surfaces`, `award_trace_badges`, and (if the trace has a route) 6 `generate_tiles` jobs (zooms 7–12).
2. `extract_surfaces` runs first, calls `_extract_surfaces()`, then sets `status = "surface_extracted"`.
3. `award_trace_badges` checks the trace status. If not yet `surface_extracted`, it reschedules itself after 5 seconds. Otherwise it calls `award_badges()` then sets `status = "analyzed"`.
4. `generate_tiles` checks the trace status. If still `not_analyzed`, it reschedules itself after 5 seconds. Otherwise it generates PNG tiles for the trace's bbox at the requested zoom level.
5. The trace detail page polls `/api/traces/<uuid>/status/` every 5 seconds and reloads when the status changes (both intermediate and final transitions).

## Catch-up command

If traces are stuck in `not_analyzed` or `surface_extracted` (e.g., worker was down), run:

```bash
python manage.py analyze_traces
```

This defers the appropriate jobs:
- `not_analyzed` traces → `extract_surfaces` + `award_trace_badges`
- `surface_extracted` traces → `award_trace_badges` only
