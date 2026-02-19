# NYC Taxi Trips - Urban Mobility Data Explorer
Full-stack analytics system for NYC taxi trips with a data cleaning pipeline, SQLite database, Flask API, and a frontend dashboard.

## Teamsheet Link
**Team_Task_Sheet**:(https://docs.google.com/spreadsheets/d/14I3UKPqRwpI2tbFXUVgtxqpWFk0YGLgRzVdfIVEYAnA/edit?usp=sharing)

## Architecture
**System diagram**: (https://drive.google.com/file/d/1paM_y9yGavcYh1p_ihe1HPoM7qEZtic9/view?usp=sharing)

## Prerequisites
- Python 3.10+ (tested with 3.11)
- pip and virtualenv

## Data Requirements
Place the TLC files in these locations:
- `data/parquet/yellow_tripdata_2019-01.parquet`
- `data/parquet/taxi_zone_lookup.parquet`
- `data/geojson/taxi_zones.geojson`

If your raw files are CSV or shapefiles, use the conversion scripts below.

## Setup
Create and activate a virtual environment:
```
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

## Data Pipeline
Optional conversions:
```
python convert_csv_to_parquet.py
python convert_shp_to_geojson.py
```

Run the pipeline (creates cleaned trips + zones files and exclusion logs):
```
python data_pipeline/run_pipeline.py
```

Outputs:
- `data/processed/cleaned_trips.csv`
- `data/processed/zones_cleaned.csv`
- `data/processed/zones_geo_cleaned.geojson`
- `data/logs/excluded_records.csv`

## Database Initialization
Build the SQLite database from the processed files:
```
python backend/init_db.py
```

This creates/updates:
- `database/nyc_taxi.db`
- schema at `database/schema.sql`

## Run the Backend
```
python backend/app.py
```

Health check: `http://127.0.0.1:5000/health`

## Run the Frontend
```
cd nyc-frontend
python -m http.server 5173
```

Open `http://127.0.0.1:5173`

## API Endpoints
- `GET /api/trips` (filters: `start_date`, `end_date`, `min_distance`, `max_distance`, `min_fare`, `max_fare`, `is_peak_hour`, `is_weekend`, `pickup_borough`, `pickup_zone`, `dropoff_borough`, `dropoff_zone`, `pu_location_id`, `do_location_id`)
- `GET /api/summary`
- `GET /api/heatmap`
- `GET /api/top_routes`
- `GET /api/temporal_analysis`
- `GET /api/zones`
- `GET /api/zones/boroughs`
- `GET /api/zones/geojson`

## Deliverables (placeholders)
- Video walkthrough: [ADD LINK]
- PDF technical report: [ADD LINK]
- Team participation sheet: [ADD LINK]
- Database dump/schema files: [ADD LINK OR PATH]

## Project Structure
```
## Project Stucture
```
```
NYC_Taxi_trips/
│
├── data_pipeline/                
│   ├── load_raw_data.py
│   ├── clean_trips.py
│   ├── feature_engineering.py
│   ├── excluded_records.py
│   ├── run_pipeline.py
│
├── data/                         
│   ├── raw/                       
│   ├── parquet/                   
│   ├── geojson/                  
│   ├── taxi_zones/                
│   │   ├── taxi_zones.dbf
│   │   ├── taxi_zones.prj
│   │   ├── taxi_zones.sbn
│   │   ├── taxi_zones.sbx
│   │   ├── taxi_zones.shp
│   │   ├── taxi_zones.shp.xml
│   │   └── taxi_zones.shx
│   └── cleaned_data/              
│
├── docs/                          
│   ├── pipeline/                  
│   │   ├── download_raw_and_cleaned-data.md  
│   │   ├── Option_A.png                         
│   │   └── Pipeline_guide.md                    
│
├── convert_csv_to_parquet.py      
├── convert_shp_to_geojson.py      
├── requirements.txt               
├── .gitignore                     
├── README.md                      
│
├──backend/
|  ├── app.py              # Main entry point (Server & Config)
|  ├── api.py              # Route definitions & Logic 
|  ├── database.py         # Database connection helper
|  ├── algorithms.py       # Manual algorithm implementations (Bubble Sort, etc.)
|  ├── init_db.py          # Database initialization script
|  └── requirements.txt    # Python dependencies  
├──database/
|  ├── schema.sql
|                  
├── frontend/
|  ├── index.html
|  ├── style.css
|  ├── app.js                     

```