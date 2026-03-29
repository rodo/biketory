# Biketory

A Django application for uploading GPX traces and visualising closed geographic surfaces on a map.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Stack

- **Python 3.12** / **Django 6.0**
- **PostgreSQL** + **PostGIS** — spatial database
- **GeoDjango** (`django.contrib.gis`) — geographic models and queries
- **psycopg2-binary** — PostgreSQL adapter
- **gpxpy** — GPX file parsing
- **Leaflet.js** + **Turf.js** — frontend map (loaded via CDN)

## Project structure

```
biketory/          Django project package (settings, urls, wsgi)
traces/            Main application
  models.py        Trace, ClosedSurface, Hexagon, HexagonScore, UserProfile, Friendship, UserSurfaceStats
  forms.py         TraceUploadForm
  urls.py
  views/
    landing.py       Public map page (all closed surfaces, no limit)
    upload.py        GPX upload (login required)
    register.py      Account creation
    trace_list.py    List of all traces (login required)
    trace_detail.py  Trace map with route/surfaces/hexagons layers (login required)
    delete_trace.py  Trace deletion (login required)
    hexagon_detail.py JSON API — top scores for a hexagon (public)
    profile.py       User profile with stats and hexagon map (login required)
    friends.py       Friend search, requests, accept/decline/remove (login required)
    legal.py         Legal notice page (public)
  templates/
    base.html                    Shared top bar layout ({% block topbar_extra %} slot)
    traces/landing.html          Full-screen Leaflet map with hexagon dissolve
    traces/upload.html           GPX drop-zone form
    traces/trace_list.html       Traces table
    traces/trace_detail.html     Map with 3 toggleable layers: trace, surfaces, hexagons
    traces/profile.html          User stats, hexagon map, friends summary
    traces/friends.html          Friend search, pending requests, friends list
    traces/legal.html            Legal notice
    registration/login.html
    registration/register.html
  management/commands/
    generate_hexagon_tiles.py    Generate static PNG tiles for hexagons
    generate_premium_user_tiles.py  Generate static tiles per premium user
    purge_surfaces.py            Delete all surfaces and reset extraction flags
    reset_data.py                Reset all data (traces, badges, hexagons). DEBUG only
```

## Models

| Model | Key fields |
|---|---|
| `Trace` | `gpx_file`, `route` (MultiLineString), `uploaded_by` (FK User), `extracted` (bool), `status` (not_analyzed/analyzed), `first_point_date`, `uploaded_at` |
| `ClosedSurface` | `trace` (FK), `owner` (FK User), `segment_index`, `polygon` (Polygon), `detected_at` |
| `Hexagon` | `geom` (Polygon, unique), `created_at` |
| `HexagonScore` | `hexagon` (FK), `user` (FK), `points`, `last_earned_at` — unique (hexagon, user) |
| `UserProfile` | `user` (OneToOne), `daily_upload_limit` (default 5) |
| `Friendship` | `from_user` (FK), `to_user` (FK), `status` (pending/accepted), `created_at` — unique (from_user, to_user) |
| `UserSurfaceStats` | `user` (OneToOne), `total_area` (float, deg²), `union` (MultiPolygon), `secret_uuid`, `updated_at` |

## Management commands

**À chaque ajout, suppression ou modification d'une management command, mettre à jour `README.md` et cette section.**

```bash
# Compute aggregated statistics for day/week/month/year (or all)
python manage.py compute_stats {day,week,month,year,all} [--from YYYY-MM-DD] [--to YYYY-MM-DD]

# Create missing monthly sub-partitions for statistics_userdailystats
python manage.py create_daily_stats_partitions [--months-ahead 3]

# Generate static PNG tiles for all hexagons
python manage.py generate_hexagon_tiles [--zoom-min 0] [--zoom-max 10] [--clean]

# Generate static tiles per premium user with recent uploads
python manage.py generate_premium_user_tiles [--zoom-min 5] [--zoom-max 10] [--clean]

# Delete all surfaces, reset trace.extracted flags, clear user stats
python manage.py purge_surfaces [--yes]


# Defer badge analysis jobs for unanalyzed traces
python manage.py analyze_traces

# Start the procrastinate background worker (processes badges)
python manage.py procrastinate worker --processes=1

# Reset all data: traces, surfaces, hexagons, badges, stats (DEBUG only)
python manage.py reset_data [--yes]

```

## Authentication

- Login required to upload (`@login_required`)
- Django built-in auth at `/accounts/` (login, logout, password change)
- Registration at `/register/`
- After login → `/upload/`; after logout → `/`

## URL routes

| URL | View | Auth |
|---|---|---|
| `/` | `landing` | public |
| `/upload/` | `upload_trace` | required |
| `/register/` | `register` | public |
| `/traces/` | `trace_list` | required |
| `/traces/<pk>/` | `trace_detail` | required |
| `/traces/<pk>/delete/` | `delete_trace` | required |
| `/hexagons/<pk>/` | `hexagon_detail` (JSON API) | public |
| `/profile/` | `profile` | required |
| `/friends/` | `friends` | required |
| `/legal/` | `legal` | public |
| `/s/<code>/` | `shared_profile` | public |

## Landing page map

- Displays **all** `ClosedSurface` polygons (no limit)
- Hexagons are computed client-side with **Turf.js** (`hexGrid` + `booleanContains`)
- Contiguous hexagons belonging to the same user are merged via `turf.dissolve`
- Current user's hexagons: blue (`#2980b9`) — others: red (`#e74c3c`)
- Zoom level displayed in the top bar

## Trace detail map

- Three toggleable layers: **Trace** (red), **Surfaces** (blue), **Hexagons** (green)
- Hexagons loaded from `HexagonScore` linked to the trace's closed surfaces

## Database

Database name: `biketory`. Configure credentials in `biketory/settings.py` (`DATABASES`).
PostGIS extension must be enabled:
```sql
CREATE EXTENSION postgis;
```

## SQL conventions

All SQL queries must be stored in dedicated `.sql` files under `traces/sql/`, never inline in Python code. Load them at module level with `Path(__file__).resolve().parent.parent / "sql" / "my_query.sql").read_text()` and pass the result to `cursor.execute()`.

```python
# Good
_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_MY_QUERY_SQL = (_SQL_DIR / "my_query.sql").read_text()
cursor.execute(_MY_QUERY_SQL, [param1, param2])

# Bad — never do this
cursor.execute("SELECT * FROM my_table WHERE id = %s", [pk])
```

**Important:** never use `%s` in SQL comments inside `.sql` files — psycopg2 counts them as parameter placeholders.

## API Stats constraints

`traces/views/api_stats.py` must only query models from the `statistics` application. No direct access to `traces` models is allowed in this view.

## Color palette

| Role | Value |
|---|---|
| Background | `#1b2d1e` (dark forest green) |
| Accent | `#f0a500` (amber) |
| Surface | `#f5f0e8` (warm beige) |

## Test fixtures

Les traces GPX de test sont dans `trace_samples/`. Le document `doc/trace_samples.md` liste chaque fixture et les tests qui l'utilisent. **Ce document doit être mis à jour** à chaque ajout, suppression ou modification d'une fixture ou d'un test qui en dépend.

## Git workflow

La branche `main` est protégée sur GitHub. Toujours créer une nouvelle branche
avant de modifier des fichiers :

```bash
git checkout main
git checkout -b feature/<nom>
```

Ne jamais commiter ni pusher directement sur `main`.
