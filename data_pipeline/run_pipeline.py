"""
Creates cleaned_data directory
Run: (load_raw_data, clean_trips, feature_engineering, and excluded records)
Saves outputs: (cleanedd_trips.csv, zones_cleaned.csv, zones_geo_cleaned.geojson, excluded_records.csv)
skips if outputs already exists
Prevent recomputation
"""

from pathlib import Path
import pandas as pd
from load_raw_data import load_all_raw_data
from clean_trips import clean_trip_data
from feature_engineering import engineer_features
from excluded_records import merge_exclude_records


CLEANED_DIR = Path("cleaned_data")

CLEANED_TRIPS_FILE = CLEANED_DIR / "cleaned_trips.csv"
ZONES_CLEANED_FILE = CLEANED_DIR / "zones_cleaned.csv"
ZONES_GEO_FILE = CLEANED_DIR / "zones_geo_cleaned.geojson"
EXCLUDED_FILE = CLEANED_DIR / "excluded_records.csv"


def ensure_directory():
    """Create cleaned_data directory if it does not exist"""
    CLEANED_DIR.mkdir(exist_ok=True)

def run_pipeline():
    print("\n========** Starting Data Pipeline **======\n")

    ensure_directory()

    # Load raw data
    print("** Loading raw data...")
    trips_df, zones_df, geo_df = load_all_raw_data()

    # Clean GEOJSON
    if not ZONES_GEO_FILE.exists():
        print("** Cleaning GeoJSON zones...")

        geo_df.columns = geo_df.columns.str.lower()

        required_cols = ["locationid", "borough", "zone", "geometry"]
        geo_df = geo_df[required_cols]

        # Ensure CRS is WGS84 (EPSG:4326) for mapping
        if geo_df.crs is not None and geo_df.crs.to_epsg() != 4326:
            geo_df = geo_df.to_crs(epsg=4326)

        geo_df.to_file(ZONES_GEO_FILE, driver="GeoJSON", index=False)
        print("** GeoJSON zones saved **")

    else:
        print("! GeoJSON already cleaned. Skipping.")
    
    # Save zones csv
    if not ZONES_CLEANED_FILE.exists():
        print("** Saving cleaned zones CSV...")
        zones_df.to_csv(ZONES_CLEANED_FILE, index=False)
    else:
        print("! Zones CSV already exists. Skipping.")
        
    # Clean trips
    if not CLEANED_TRIPS_FILE.exists():
        print("** Running trip cleaning...")
        clean_df, excluded_clean_df = clean_trip_data(trips_df, zones_df)
        clean_df.to_csv(CLEANED_TRIPS_FILE, index=False)
    else:
        print("! Cleaned trips already exist. Loading...")
        clean_df = pd.read_csv(
            CLEANED_TRIPS_FILE,
            parse_dates=["tpep_pickup_datetime", "tpep_dropoff_datetime"]
        )
        excluded_clean_df = pd.DataFrame()


    # Feature engineering
    if "trip_duration_minutes" not in clean_df.columns:
        print("** Running feature engineering...")
        engineered_df, excluded_engineered_df = engineer_features(clean_df)
        engineered_df.to_csv(CLEANED_TRIPS_FILE, index=False)
    else:
        print("! Feature engineering already applied.")
        engineered_df = clean_df
        excluded_engineered_df = pd.DataFrame()

    # Merge and save excluded records
    excluded_df = merge_exclude_records(excluded_clean_df, excluded_engineered_df)

    if excluded_df is not None and not excluded_df.empty:
        excluded_df.to_csv(EXCLUDED_FILE, index=False)
        print(f"** Excluded records saved: {EXCLUDED_FILE}")
    else:
        print("! No excluded records to save.")

        
    print("\n========= DATA PIPELINE FINESHED SUCCESSFULLy ==========\n")


if __name__ == "__main__":
    run_pipeline()
