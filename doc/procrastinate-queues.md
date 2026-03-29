# Procrastinate queues

This document lists all procrastinate queues and tasks used in the project.
**It must be updated** whenever a queue or task is added, modified, or removed.

## Worker

```bash
python manage.py procrastinate worker --processes=1
```

A single process is used to guarantee sequential task execution.

## Queues

| Queue | Description |
|---|---|
| `default` | General-purpose queue for background tasks |

## Tasks

| Task | Queue | Queueing lock | Description |
|---|---|---|---|
| `analyze_trace` | `default` | `analyze_trace` | Award badges for a trace and set its status to `analyzed`. The queueing lock ensures only one analysis runs at a time, preserving upload order. |

## How it works

1. When a user uploads a trace, `upload.py` defers an `analyze_trace` job.
2. The worker picks up jobs sequentially (single process + queueing lock).
3. `analyze_trace` calls `award_badges()` then sets `trace.status = "analyzed"`.
4. The trace detail page polls `/api/traces/<pk>/status/` every 5 seconds and reloads when analysis is complete.

## Catch-up command

If traces are stuck in `not_analyzed` (e.g., worker was down during uploads), run:

```bash
python manage.py analyze_traces
```

This defers an `analyze_trace` job for every trace with `status="not_analyzed"`, ordered by upload date.
