## NYC Taxi Trips Data cleaning and featue engineering pipeline
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
│   ├── raw/           # Raw CSV and shapefiles (not tracked in GitHub)
│   ├── parquet/       # Converted Parquet files (not tracked)
│   ├── geojson/       # Converted GeoJSON files (not tracked)
│   ├── taxi_zones/    # 
│   └── cleaned_data/  # Output cleaned datasets (not tracked)
│
├── convert_csv_to_parquet.py
├── convert_shp_to_geojson.py
├── requirements.txt
├── .gitignore
└── README.md
```
### Data cleaning pipeline
The data pipeline will perform this following steps:
1. Load raw NYC Taxi trip data (Parquet format)
2. Load taxi zone lookup and GeoJSON zone boundaries
3. Clean and validate tri records
4. Remove invalid or inconsistent records
5. Engineer new features such as: trips duration(minutes), time-based features(hour, day)
6. Save cleaned datasets ans excluded records separately
The pipeline also avoids recomputation by skipping steps if output files already exist.

### Pipeline Workflow
The pipeline is executed using: `python data_pipeline/run_pipeline.py`
It performs the following sequence:
1. `load_raw_data.py`: Loads Parquet and GeoJSON files with proper datatypes and dattime parsing.
2. `clean_trips.py`: Filters invalid records(negative distances, duplicates, invalid locations, missing values).
3. `feature_engineering.py`: Adds derived features such as trip duration and time-based attributes, excluded records, average_speed, revenue_per_distance and peak_per_hour.
4. `excluded_records.py`: Will collect and save the excluded records from `clean_trips.py & feature_engineering.py` for auditing.
5. Saves outputs into: `cleaned_data/` direectly under project root.
The output files:
- `cleaned_trips.csv`,
- `zones_cleaned.csv`
- `zones_geo_cleaned.geojson`
- `excluded_records.csv`

## How to run Data pipeline
1. Create virtual environment
**Windows**: 
```
python -m venv venv
venv\Scripts\activate
```
**Linux**:
```
python3 -m venv venv
source venv/bin/activate
```
2. Install dependencies
From root  project run: `pip install -r requirements.txt`
3. Convert raw data
```
python convert_csv_to_parquet.py
python convert_shp_to_geojson.py
```
4. Run pipeline: `python data_pipeline/run_pipeline.py`
