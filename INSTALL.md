# Biketory — Installation

First-time setup instructions.

## Prerequisites

- **Python 3.12**
- **PostgreSQL** with **PostGIS**

## Database

```sql
CREATE DATABASE biketory;
\c biketory
CREATE EXTENSION postgis;
```

## Application

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp biketory/settings.dist biketory/settings.py
python manage.py migrate
```

## Geographic zones

Load geographic zones from GeoJSON files in `media/src/`:

```bash
python manage.py load_geozones
```

## Background workers

Surface extraction and badge analysis are processed asynchronously via [procrastinate](https://procrastinate.readthedocs.io/). Start workers with:

```bash
python manage.py procrastinate worker -q analyze,badges,tiles,challenges
```
