# Biketory

A Django application for uploading GPX traces and visualising closed geographic surfaces on a map.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp biketory/settings.dist biketory/settings.py
python manage.py migrate
python manage.py runserver
```

PostgreSQL with PostGIS is required:

```sql
CREATE DATABASE biketory;
\c biketory
CREATE EXTENSION postgis;
```

## Stack

- **Python 3.12** / **Django 6.0**
- **PostgreSQL** + **PostGIS** (GeoDjango)
- **gpxpy** for GPX file parsing
- **Leaflet.js** + **Turf.js** for the frontend map

## Management commands

| Command | Description |
|---|---|
| `compute_stats` | Compute aggregated statistics (new users, traces, surfaces, hexagons) for day/week/month/year granularities. Accepts `--from` and `--to` date range, or `all` to compute every granularity. |
| `create_daily_stats_partitions` | Create missing monthly sub-partitions on the `statistics_userdailystats` partitioned table for the current month and the next N months (`--months-ahead`, default 3). |
| `generate_hexagon_tiles` | Generate static PNG tiles for all hexagons at configurable zoom levels (`--zoom-min`, `--zoom-max`). Use `--clean` to remove existing tiles first. |
| `generate_premium_user_tiles` | Generate static PNG tiles per premium user who uploaded traces in the last 7 days (`--zoom-min`, `--zoom-max`, `--clean`). |
| `purge_surfaces` | Delete all closed surfaces, reset `extracted` flags on traces, and clear user surface stats. Requires `--yes` to skip confirmation. |
| `analyze_traces` | Defer analysis jobs for traces stuck in `not_analyzed` or `surface_extracted` status. |

## Background workers

Surface extraction and badge analysis are processed asynchronously via [procrastinate](https://procrastinate.readthedocs.io/). Start workers with:

```bash
python manage.py procrastinate worker -q surface_extraction,badges
```

| `expire_premium` | Set `is_premium=False` on user profiles with no active subscription. Run daily via cron. |
| `reset_data` | Delete all traces, surfaces, hexagons, badges, and stats. Only works with `DEBUG=True`. Requires `--yes` to skip confirmation. |

