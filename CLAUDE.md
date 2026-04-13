# Biketory

A Django application for uploading GPX traces and visualising closed geographic surfaces on a map.

## Domain vocabulary

| Term | Definition |
|---|---|
| **Acquired hexagon** (acquis) | A hexagon that falls within a user's trace. Each time a user's trace crosses a hexagon, its `HexagonScore.points` for that user is incremented. |
| **Conquered hexagon** (conquis) | A hexagon where the user holds the highest `points` among all users. If user A has 2 points and user B has 3 points on the same hexagon, it is conquered by B. |

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
  models.py        Trace, ClosedSurface, Hexagon, HexagonScore, UserProfile, Friendship, UserSurfaceStats, StravaImport
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
    cluster_leaderboard.py  Largest contiguous cluster leaderboard (login required)
    leaderboard.py   Leaderboard — conquered & acquired hexagons (login required)
    subscription_history.py  Subscription history (login required)
    strava_import.py Strava activity import (login required)
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
    notifs/notifications.html    Notifications list
    registration/login.html
    registration/register.html
  management/commands/
    generate_hexagon_tiles.py    Generate static PNG tiles for hexagons
    generate_premium_user_tiles.py  Generate static tiles per premium user
    purge_surfaces.py            Delete all surfaces and reset extraction flags
    reset_data.py                Reset all data (traces, badges, hexagons). DEBUG only
referrals/         Referral/invitation system
  models.py        Referral
  forms.py         ReferralForm
  emails.py        send_referral_email
  views.py         referral_list (login required)
  urls.py
  tests/
    test_models.py
    test_views.py
challenges/        Challenges system
  models.py        Challenge, ChallengeHexagon, ChallengeParticipant, ChallengeLeaderboardEntry, ChallengeSponsor, ChallengeReward, Dataset, DatasetFeature, ChallengeDatasetScore
  admin.py         Challenge admin with inlines
  urls.py
  views/
    challenge_list.py       List of challenges (login required)
    challenge_detail.py     Challenge detail + leaderboard + join (login required)
    admin_challenges.py     Admin dashboard: list, create, detail (superuser)
    api_hexagons.py         API JSON: generate/list hexagons in bbox (superuser)
  sql/
    challenge_score_capture.sql  Score for capture_hexagon challenges
    challenge_score_points.sql   Score for max_points challenges
    challenge_score_dataset_points.sql  Score for dataset_points challenges
    score_dataset_on_upload.sql  Spatial join: dataset features in trace hexagons
  scoring.py                Score dataset_points challenges on trace upload
  tasks.py                  Procrastinate task: compute_challenge_leaderboards
  rewards.py                Award badges + subscriptions to challenge winners
  tests/
    test_models.py
    test_views.py
    test_tasks.py
geozones/          Geographic zones application
  models.py        GeoZone, ZoneLeaderboardEntry, MonthlyZoneRanking
  admin.py         GeoZone admin with Leaflet map
  urls.py
  views/
    zone_leaderboard.py  Per-zone leaderboard (premium, login required)
  sql/
    zone_leaderboard_conquered.sql  Conquered hexagons per zone
    zone_leaderboard_acquired.sql   Acquired hexagons per zone
    user_best_zone_month.sql        Top 3 best monthly rankings per zone for a user
    user_current_zone_ranks.sql     Live zone rankings for a user
  management/commands/
    load_geozones.py               Load zones from media/src/ GeoJSON files
    compute_zone_leaderboard.py    Compute per-zone leaderboard entries
```

## Models

| Model | Key fields |
|---|---|
| `Trace` | `gpx_file`, `route` (MultiLineString), `uploaded_by` (FK User), `extracted` (bool), `status` (not_analyzed/analyzed), `first_point_date`, `uploaded_at` |
| `ClosedSurface` | `trace` (FK), `owner` (FK User), `segment_index`, `polygon` (Polygon), `detected_at` |
| `Hexagon` | `geom` (Polygon, unique), `owner` (FK User, nullable), `owner_points` (int, nullable), `owner_claimed_at` (datetime, nullable), `created_at` |
| `HexagonScore` | `hexagon` (FK), `user` (FK), `points`, `last_earned_at` — unique (hexagon, user) |
| `UserProfile` | `user` (OneToOne), `daily_upload_limit` (default 5), `is_premium` (bool, default False) |
| `Friendship` | `from_user` (FK), `to_user` (FK), `status` (pending/accepted), `created_at` — unique (from_user, to_user) |
| `UserSurfaceStats` | `user` (OneToOne), `total_area` (float, deg²), `union` (MultiPolygon), `secret_uuid`, `updated_at` |
| `Notification` | `user` (FK User), `notification_type` (badge_awarded/friend_request/friend_accepted/trace_analyzed/referral_signup), `message`, `link`, `is_read`, `created_at` |
| `Referral` | `sponsor` (FK User), `email`, `token` (unique), `status` (pending/accepted), `referee` (FK User, null), `created_at`, `accepted_at`, `rewarded` — unique (sponsor, email) |
| `StravaImport` | `user` (FK User), `strava_activity_id` (BigInt), `trace` (OneToOne Trace, null), `imported_at` — unique (user, strava_activity_id) |
| `Subscription` | `user` (FK User), `start_date`, `end_date`, `created_at` — ordered by `-start_date` |
| `GeoZone` | `code` (unique), `name`, `admin_level` (OSM admin_level, 2=country), `parent` (self FK), `geom` (MultiPolygon 4326), `loaded_at` |
| `ZoneLeaderboardEntry` | `zone` (FK GeoZone), `user_id`, `username`, `is_premium`, `hexagons_conquered`, `hexagons_acquired`, `rank_conquered`, `rank_acquired`, `computed_at` — unique (zone, user_id) |
| `MonthlyZoneRanking` | `zone` (FK GeoZone), `period` (Date, 1st of month), `user_id`, `username`, `is_premium`, `hexagons_conquered`, `hexagons_acquired`, `rank_conquered`, `rank_acquired`, `computed_at` — unique (zone, period, user_id) |
| `ClusterLeaderboardEntry` | `user_id` (int, unique), `username`, `is_premium`, `largest_cluster_hex_count`, `largest_cluster_area_m2` (float), `largest_cluster_geom` (MultiPolygon 4326), `rank`, `computed_at` |
| `Challenge` | `title`, `description`, `challenge_type` (capture_hexagon/max_points/active_days/new_hexagons/distinct_zones/dataset_points/visit_hexagons), `capture_mode` (any/all, nullable), `premium_only`, `is_visible` (bool, default False), `geozone` (FK GeoZone, nullable), `dataset` (FK Dataset, nullable), `goal_threshold` (PositiveInt, nullable), `zone_admin_level` (PositiveSmallInt, nullable), `hexagons_per_zone` (PositiveInt, nullable), `rewards_awarded_at` (datetime, nullable), `start_date`, `end_date`, `created_by` (FK User), `created_at` |
| `ChallengeHexagon` | `challenge` (FK), `hexagon` (FK) — unique (challenge, hexagon) |
| `ChallengeParticipant` | `challenge` (FK), `user` (FK), `score` (IntegerField, default 0), `joined_at` — unique (challenge, user) |
| `ChallengeLeaderboardEntry` | `challenge` (FK), `user_id`, `username`, `is_premium`, `score`, `goal_met` (bool, default True), `rank`, `computed_at` — unique (challenge, user_id) |
| `ChallengeSponsor` | `challenge` (FK), `name`, `logo` (ImageField, nullable), `url` |
| `ChallengeReward` | `challenge` (FK), `rank_threshold`, `reward_type` (badge/subscription_3m/subscription_6m/subscription_1y), `badge_id` — unique (challenge, rank_threshold, reward_type) |
| `Dataset` | `name`, `source_file` (CharField 500), `md5_hash` (CharField 32, unique), `feature_count` (PositiveInt, default 0), `imported_at` |
| `DatasetFeature` | `dataset` (FK Dataset), `geom` (PointField 4326), `properties` (JSONField), `created_at` — GIST index on `geom` |
| `ChallengeDatasetScore` | `challenge` (FK Challenge), `user` (FK User), `dataset_feature` (FK DatasetFeature), `trace` (FK Trace), `earned_at` — unique (challenge, user, dataset_feature). SQL trigger auto-increments `ChallengeParticipant.score` on insert. |

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

# Generate static PNG tiles with score labels at hexagon centroids
python manage.py generate_score_tiles [--zoom-min 5] [--zoom-max 10] [--clean]

# Delete all surfaces, reset trace.extracted flags, clear user stats
python manage.py purge_surfaces [--yes]


# Compute the leaderboard (hexagons conquered & acquired)
python manage.py compute_leaderboard

# Compute the largest contiguous cluster leaderboard
python manage.py compute_cluster_leaderboard

# Load geographic zones from media/src/ GeoJSON files
python manage.py load_geozones

# Compute per-zone leaderboard (all zones or single --zone-code)
python manage.py compute_zone_leaderboard [--zone-code FR] [--snapshot-month YYYY-MM]

# Defer badge analysis jobs for unanalyzed traces
python manage.py analyze_traces

# Start the procrastinate background worker (processes badges)
python manage.py procrastinate worker --processes=1

# Expire premium: set is_premium=False on profiles with no active subscription
python manage.py expire_premium

# Backfill Hexagon.owner from HexagonScore (highest points, latest earned_at)
python manage.py backfill_hexagon_owners

# Reset all data: traces, surfaces, hexagons, badges, stats (DEBUG only)
python manage.py reset_data [--yes]

# Import GeoJSON Point datasets from data/ directory
python manage.py load_dataset [--path <file>] [--name <name>]

# Defer challenge leaderboard recomputation task
python manage.py compute_challenge_leaderboards

```

## Authentication

- Login required to upload (`@login_required`)
- Django built-in auth at `/accounts/` (login, logout, password change)
- Registration at `/register/`
- After login → `/dashboard/`; after logout → `/`

## URL routes

| URL | View | Auth |
|---|---|---|
| `/` | `landing` | public |
| `/dashboard/` | `dashboard` | required |
| `/upload/` | `upload_trace` | required |
| `/register/` | `register` | public |
| `/traces/` | `trace_list` | required |
| `/traces/<pk>/` | `trace_detail` | required |
| `/traces/<pk>/delete/` | `delete_trace` | required |
| `/hexagons/<pk>/` | `hexagon_detail` (JSON API) | public |
| `/profile/` | `dashboard` (legacy alias) | required |
| `/friends/` | `friends` | required |
| `/leaderboard/` | `leaderboard` | required |
| `/leaderboard/surface/` | `cluster_leaderboard` | required |
| `/leaderboard/zone/<code>/` | `zone_leaderboard` | required + premium |
| `/pricing/` | `pricing` | public |
| `/s/<code>/` | `shared_profile` | public |
| `/notifications/` | `notifications_list` | required |
| `/notifications/mark-read/` | `notifications_mark_read` (POST, JSON) | required |
| `/referrals/` | `referral_list` | required |
| `/strava/activities/` | `strava_activities` | required |
| `/strava/import/` | `strava_import` (POST) | required |
| `/subscriptions/` | `subscription_history` | required |
| `/challenges/` | `challenge_list` | required |
| `/challenges/<pk>/` | `challenge_detail` | required |
| `/challenges/<pk>/join/` | `join_challenge` (POST) | required |
| `/admin-dashboard/challenges/` | `admin_challenges` | superuser |
| `/admin-dashboard/challenges/create/` | `admin_challenge_create` | superuser |
| `/admin-dashboard/challenges/<pk>/` | `admin_challenge_detail` | superuser |
| `/api/challenges/hexagons/` | `api_challenge_hexagons` | superuser |

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

All SQL queries must be stored in dedicated `.sql` files under their app's `sql/` directory (e.g. `traces/sql/`, `statistics/sql/`, `geozones/sql/`), never inline in Python code. Load them at module level with `Path(__file__).resolve().parent.parent / "sql" / "my_query.sql").read_text()` and pass the result to `cursor.execute()`.

```python
# Good
_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_MY_QUERY_SQL = (_SQL_DIR / "my_query.sql").read_text()
cursor.execute(_MY_QUERY_SQL, [param1, param2])

# Bad — never do this
cursor.execute("SELECT * FROM my_table WHERE id = %s", [pk])
```

**Important:** never use `%s` in SQL comments inside `.sql` files — psycopg2 and psycopg3 count them as parameter placeholders.

## Map tile source

All Leaflet maps **must** use the tile URL from `settings.TILE_SERVER_URL`, exposed in templates as `{{ tile_server_url }}` via the `traces.context_processors.tile_server` context processor. **Never hardcode a tile URL** (e.g. `https://{s}.tile.openstreetmap.org/…`) in templates or JavaScript.

All Leaflet maps **must** include OpenStreetMap copyright attribution. Use the standard format below — every `L.tileLayer` call must have an `attribution` option.

```javascript
// Good
L.tileLayer('{{ tile_server_url }}', {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

// Bad — never do this
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { ... });
```

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
