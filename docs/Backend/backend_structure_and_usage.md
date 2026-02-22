# Backend Structure and Usage

This document reflects the current backend implementation after the performance and data-flow updates.

## Backend Responsibilities
- Serve API endpoints for trips, summaries, temporal analytics, routes, and map data.
- Serve static zone files (`zones_cleaned.csv`, `zones_geo_cleaned.geojson`) from `cleaned_data/`.
- Query SQLite (`database/nyc_taxi.db`) using filterable SQL.
- Apply manual sorting algorithm when requested.
- Cache API responses in memory to reduce repeated query cost.

## Current Backend Layout
```text
backend/
├── app.py
├── api.py
├── algorithms.py
├── database.py
├── init_db.py
├── clean_data.py
├── clean_transform.py
└── requirements.txt
```

## File Roles

### `backend/app.py`
- Creates Flask app.
- Enables CORS.
- Registers API blueprint from `api.py`.
- Exposes static cleaned-data files through:
  - `/cleaned_data/zones_cleaned.csv`
  - `/cleaned_data/zones_geo_cleaned.geojson`
- Health endpoint: `/health`.

### `backend/api.py`
- Implements all REST endpoints.
- Centralized query helpers:
  - `build_where_clause(...)`
  - `query_trips_payload(...)`
  - `query_summary_payload(...)`
- Implements in-memory TTL response cache:
  - `_cache_key`, `_cache_get`, `_cache_set`.
- Implements performance-split dashboard endpoint:
  - `GET /api/dashboard`
  - `include_summary=true|false`
  - `include_trips=true|false`.

### `backend/algorithms.py`
- Manual iterative merge sort:
  - `manual_merge_sort_trips(...)`
- Compatibility wrapper:
  - `manual_bubble_sort_trips_by_fare(...)` delegates to merge sort.
- Manual range filter:
  - `manual_filter_trips_by_distance(...)`.

### `backend/init_db.py`
- Creates schema from `database/schema.sql`.
- Loads trips from `cleaned_data/cleaned_trips.csv`.
- Adds additional runtime indexes.
- Runs `VACUUM` after load.

## Database Notes
- Database engine: SQLite.
- Main fact table: `trips`.
- Dimension table still present: `payment_types`.
- Zone tables exist in schema (`zones`, `zones_geo`) but current frontend flow reads zone metadata from cleaned-data static files.

## Endpoint Reference (Operational)

### Core
- `GET /api/dashboard`
  - Returns:
    - `summary` (optional)
    - `trips` (optional)
  - Key params:
    - `page`, `per_page`, `sort`, `order`
    - `include_summary`, `include_trips`
    - `custom_sort`
    - filter params from `build_where_clause`.

### Additional
- `GET /api/trips`
- `GET /api/summary`
- `GET /api/heatmap`
- `GET /api/top_routes`
- `GET /api/temporal_analysis`
- `GET /api/zones`
- `GET /api/zones/boroughs`
- `GET /api/zones/geojson`

## Data Filtering Strategy (Current)
- Frontend converts borough/zone selections to location ID filters.
- Backend currently relies on:
  - `pu_location_id`, `do_location_id`
  - `pu_location_ids`, `do_location_ids`
- Core trips/summary queries do not require zone-table joins.

## Performance Strategy (Current)
- Server-side response caching (TTL).
- Dashboard split payload to avoid expensive summary blocking trips/map.
- Summary caching keyed by filter signature.
- Optional manual merge-sort path for assignment algorithm requirement.

## Run Backend
From project root:
```bash
python backend/init_db.py
python backend/app.py
```

Verify:
- `http://localhost:5000/health`
- `http://localhost:5000/apidocs`
- `http://localhost:5000/api/dashboard?page=1&per_page=100&sort=pickup_datetime&order=desc&include_summary=false&include_trips=true`
