# Biketory

A Django application for uploading GPX traces and visualising closed geographic surfaces on a map.

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
| `generate_score_tiles` | Generate static PNG tiles with score labels at hexagon centroids (`--zoom-min`, `--zoom-max`, `--clean`). Stored in `tiles/scores/`. |
| `purge_surfaces` | Delete all closed surfaces, reset `extracted` flags on traces, and clear user surface stats. Requires `--yes` to skip confirmation. |
| `analyze_traces` | Defer analysis jobs for traces stuck in `not_analyzed` or `surface_extracted` status. |
| `compute_leaderboard` | Compute the leaderboard (hexagons conquered & acquired). |
| `compute_cluster_leaderboard` | Compute the largest contiguous cluster leaderboard (users ranked by their biggest connected group of conquered hexagons). |
| `load_geozones` | Load geographic zones from GeoJSON files in `media/src/`. |
| `compute_zone_leaderboard` | Compute leaderboard per geographic zone (hexagons conquered & acquired). Accepts `--zone-code` for a single zone. |
| `expire_premium` | Set `is_premium=False` on user profiles with no active subscription. Run daily via cron. |
| `purge_jobs` | Delete all procrastinate jobs and events. Only works with `DEBUG=True`. |
| `reset_data` | Delete all traces, surfaces, hexagons, badges, and stats. Only works with `DEBUG=True`. Requires `--yes` to skip confirmation. |
| `load_dataset` | Import GeoJSON Point datasets from `data/` directory. Accepts `--path` for a specific file and `--name` for a custom name. Skips files already imported (MD5 check). |
| `compute_challenge_leaderboards` | Defer the procrastinate task that recomputes all active challenge leaderboards. |

## Challenges

Temporary challenges linked to hexagons. An admin creates a challenge via the admin dashboard, selects target hexagons on a Leaflet map (with on-the-fly generation), and players explicitly register. A leaderboard is recomputed every 3h via procrastinate. The top 3 can earn a badge and/or a subscription.

Two challenge types:
- **capture_hexagon**: count hexagons owned by the participant among the challenge hexagons
- **max_points**: sum of HexagonScore.points earned during the challenge period on challenge hexagons

## Deployment

```bash
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py compress
python manage.py collectstatic --noinput
```
