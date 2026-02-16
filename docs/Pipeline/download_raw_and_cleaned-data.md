# Download Raw and Cleaned Data
- Due to GitHub file size limitations, the project datasets (CSV, Parquet, and GeoJSON) are hosted externally on Google Drive and provided as compressed archives.

- You may choose one of the following two options depending on your needs:
       - **Option A**: Download cleaned_data only.
       _ **Option B**: Download raw data and run the full pipeline data from scratch.

## Option A: Use Cleaned  Data
- Recommended if yu don't want to run full data processing pipeline. This cleaned data is the one use for backend and frontend.

1. **Cleaned_data Link**: (`https://drive.google.com/file/d/1Z_WFoA-xPxYNFa-x4TENL1Y4XblW2CW6/view?usp=sharing`)
2. Extract the downloaded folder into the project root directory: `cleaned_data/`
3. Run pipeline: Just for check up if all files cleaned up are present.
       - Windows: `python data_pipeline/run_pipeline.py`
       - Linux : `python3 data_pipeline/runpipeline.py`

- Files contained in cleaned_data: 
                  - `cleaned_trips.csv`
                  - `zones_cleaned.csv`
                  - `zones_geo_cleaned.geojson`
                  - `excluded_records.csv`

Check the **image** named **Option_A** to see what you get if you choose option_A.


## Option B: Start from Raw data
The option is here is when you want to restart the whole data processing from raw datasets.

1. Download Raw Data
**Raw_data Link**: (`https://drive.google.com/file/d/12eRk5ZE5KwkeeKcJAdHzxS9MF0UQA9Bp/view?usp=sharing`)

- After extraction the directory should look like:
```
data/
├── raw/
│   ├── yellow_tripdata_2019-01.csv
│   └── taxi_zone_lookup.csv
├── parquet/
│   ├── yellow_tripdata_2019-01.parquet
│   └── taxi_zone_lookup.parquet
├── taxi_zones/
└── geojson/
    └── taxi_zones.geojson
```

- As you can see the link to download already contains `parquet` and `geojson` directories.
- To regenerate from scratch, delete the `parquet/` and `geojson/` directories.

2. Create virtual environment
- **Windows**: `python -m venv venv`
- **Linux**: `python3 -m venv venv`

3. Install dependencies
- **Run**: `pip install -r requirements.txt`

4. Converting raw files csv to parquet
- **Windows**:
```
python convert_csv_to_parquet.py
python convert_shp_to_geojson.py
python data_pipeline/run_pipeline.py
```
- **Linux**:
```
python3 convert_csv_to_parquet.py
python3 convert_shp_to_geojson.py
python3 data_pipeline/run_pipeline.py
```

**Note**: All these comand should be run from root project directory.
