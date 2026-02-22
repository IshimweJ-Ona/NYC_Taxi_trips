# NYC Taxi Trips - Urban Mobility Data Explorer

Enterprise-style fullstack analytics project for NYC taxi mobility patterns using TLC trip, lookup, and zone boundary data.

## Team Artifacts
- **Team participation sheet**: (https://docs.google.com/spreadsheets/d/14I3UKPqRwpI2tbFXUVgtxqpWFk0YGLgRzVdfIVEYAnA/edit?usp=sharing)

- **Architecture diagram**: https://drive.google.com/file/d/1paM_y9yGavcYh1p_ihe1HPoM7qEZtic9/view?usp=sharing

## What This Project Does
- Cleans and engineers trip-level mobility features from NYC taxi data.
- Loads cleaned trips into a normalized SQLite schema with indexes.
- Exposes a Flask REST API for filtering, sorting, summary statistics, and dashboard payloads.
- Serves an interactive frontend dashboard (charts, table, map, filters).
- Uses custom manual algorithms (merge sort) in backend and frontend code paths.

## Tech Stack
- Backend: Python, Flask, Flask-CORS, Flasgger, SQLite
- Data processing: Pandas, GeoPandas
- Frontend: HTML, CSS, JavaScript, Chart.js, Leaflet

## Data Inputs and Outputs
This repository supports two practical data-start modes:

### Mode A (Recommended): Start from pre-cleaned assets
Expected folder at project root:
- `cleaned_data/cleaned_trips.csv`
- `cleaned_data/zones_cleaned.csv`
- `cleaned_data/zones_geo_cleaned.geojson`
- `cleaned_data/excluded_records.csv` (optional log artifact)

### Mode B: Start from raw data and run full pipeline
Expected raw/converted assets:
- `data/parquet/yellow_tripdata_2019-01.parquet`
- `data/parquet/taxi_zone_lookup.parquet`
- `data/geojson/taxi_zones.geojson`

Then run pipeline to produce:
- `data/processed/cleaned_trips.csv`
- `data/processed/zones_cleaned.csv`
- `data/processed/zones_geo_cleaned.geojson`
- `data/logs/excluded_records.csv`

Notes:
- Backend runtime currently loads trips from `cleaned_data/cleaned_trips.csv` via `backend/init_db.py`.
- Frontend loads zone metadata directly through backend static routes:
  - `/cleaned_data/zones_cleaned.csv`
  - `/cleaned_data/zones_geo_cleaned.geojson`

## Prerequisites
- Python 3.10+
- `pip`

## Installation
From project root (`NYC_Taxi_trips`):

### Windows
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Linux/Mac
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

## Database Setup
Initialize the SQLite database from cleaned trips:
```bash
python backend/init_db.py
```

Creates/updates:
- `database/nyc_taxi.db`
- schema from `database/schema.sql`
- additional indexes from `backend/init_db.py`

## Run the Backend API
```bash
python backend/app.py
```

Backend defaults:
- host: `0.0.0.0`
- port: `5000`
- Swagger docs: `http://localhost:5000/apidocs`
- health: `http://localhost:5000/health`

## Run the Frontend Dashboard
Use a static server from project root:
```bash
python -m http.server 5500
```

Open:
- `http://localhost:5500/nyc-frontend/index.html`

## API Endpoints (Current)

### Core dashboard
- `GET /api/dashboard`
  - Supports:
    - pagination/sort: `page`, `per_page`, `sort`, `order`
    - filtering: date, distance, fare, peak/weekend, payment, location IDs
    - algorithm toggle: `custom_sort=true|false`
    - payload split for performance:
      - `include_summary=true|false`
      - `include_trips=true|false`

### Other endpoints
- `GET /api/trips`
- `GET /api/summary`
- `GET /api/heatmap`
- `GET /api/top_routes`
- `GET /api/temporal_analysis`
- `GET /api/zones`
- `GET /api/zones/boroughs`
- `GET /api/zones/geojson`

### Static cleaned-data routes used by frontend
- `GET /cleaned_data/zones_cleaned.csv`
- `GET /cleaned_data/zones_geo_cleaned.geojson`

## Performance Logic Implemented
- Backend in-memory TTL cache for major endpoints.
- Split dashboard payload (`include_summary`/`include_trips`) to avoid blocking table/map on heavy aggregates.
- Frontend request dedupe and cancellation via `AbortController`.
- Frontend short-lived dashboard cache.
- Debounced filter-triggered requests.
- Fast map rendering defaults and canvas-based Leaflet rendering.

## Manual Algorithm Requirement (DSA)
- Backend:
  - `backend/algorithms.py` implements iterative merge sort (`manual_merge_sort_trips`) with no built-in sort.
- Frontend:
  - `nyc-frontend/algorithms.js` implements manual merge sort and unique extraction helpers.

## Project Structure
```text
NYC_Taxi_trips/
├── backend/
│   ├── app.py
│   ├── api.py
│   ├── algorithms.py
│   ├── database.py
│   ├── init_db.py
│   ├── clean_data.py
│   ├── clean_transform.py
│   └── requirements.txt
├── nyc-frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── algorithms.js
├── data_pipeline/
│   ├── load_raw_data.py
│   ├── clean_trips.py
│   ├── feature_engineering.py
│   ├── excluded_records.py
│   └── run_pipeline.py
├── database/
│   └── schema.sql
├── docs/
│   ├── Backend/
│   ├── Pipeline/
│   ├── report/
│   └── architecture_system_design_images/
├── convert_csv_to_parquet.py
├── convert_shp_to_geojson.py
├── requirements.txt
└── README.md
```

## Typical Run Order
1. Install dependencies.
2. Ensure cleaned assets exist in `cleaned_data/` (or run full pipeline).
3. Run `python backend/init_db.py`.
4. Run `python backend/app.py`.
5. Run `python -m http.server 5500`.
6. Open dashboard URL.

## Notes
- `backend/init_db.py` currently loads only `cleaned_data/cleaned_trips.csv` into DB.
- Zone CSV/GeoJSON are consumed by frontend from backend static route, not from DB.
- If you change data files, restart backend to refresh in-memory cache behavior.
- Read the guidelines from `docs` directory to fully understand the concept.
- In **docs** directory under **pipeline/** you will find more files one contains steps to get cleaned_data and start on going anoter explains how **data_pipeline/** works or runs.
- In **docs** ypu will see also **Backend/** it also contains a file that explains backend concept
