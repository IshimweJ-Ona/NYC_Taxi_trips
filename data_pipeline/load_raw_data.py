"""
Loads the CSV raw data files from raw/ folder.
Select needed columns
Define datatypes
Convert datetime columns
Standardize column names
"""

"""
Loads the raw data files (Parquet + GeoJSON).
Select needed columns
Define datatypes
Convert datetime columns
Standardize column names
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path

# -----------------------
# Paths
# -----------------------
DATA_DIR = Path("data")
PARQUET_DIR = DATA_DIR / "parquet"
GEOJSON_DIR = DATA_DIR / "geojson"

TRIPS_FILE = PARQUET_DIR / "yellow_tripdata_2019-01.parquet"
ZONES_FILE = PARQUET_DIR / "taxi_zone_lookup.parquet"
GEO_FILE = GEOJSON_DIR / "taxi_zones.geojson"


def load_trip_data():
    """
    Load yellow tripdata from Parquet with dtype and datetime parsing.
    """
    dtype_map = {
        "VendorID": "Int64",
        "passenger_count": "Int64",
        "trip_distance": "float32",
        "RatecodeID": "Int64",
        "PULocationID": "Int64",
        "DOLocationID": "Int64",
        "payment_type": "Int64",
        "fare_amount": "float32",
        "extra": "float32",
        "mta_tax": "float32",
        "tip_amount": "float32",
        "tolls_amount": "float32",
        "improvement_surcharge": "float32",
        "total_amount": "float32",
        "congestion_surcharge": "float32",
        "store_and_fwd_flag": "string"
    }

    parse_dates = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]

    print("** Loading trip data from Parquet ...")
    trips_df = pd.read_parquet(TRIPS_FILE)

    # Ensure datetime parsing
    for dt_col in parse_dates:
        trips_df[dt_col] = pd.to_datetime(trips_df[dt_col], errors="coerce")

    trips_df = trips_df.astype(dtype_map, errors="ignore")
    trips_df.columns = trips_df.columns.str.lower()

    print(f"** Trip data loaded: {trips_df.shape} **")
    return trips_df


def load_zone_lookup():
    """
    Load taxi_zone_lookup from Parquet and standardize column names.
    """
    print("** Loading zone lookup data from Parquet ...")
    zones_df = pd.read_parquet(ZONES_FILE)
    zones_df.columns = zones_df.columns.str.lower()
    print(f"** Zone lookup loaded: {zones_df.shape} **")
    return zones_df


def load_geojson_zones():
    """
    Load GeoJSON zones.
    """
    print("** Loading GeoJSON zones ...")
    geo_df = gpd.read_file(GEO_FILE)
    geo_df.columns = geo_df.columns.str.lower()
    return geo_df


def load_all_raw_data():
    """
    Loader function used by run_pipeline.py
    Returns trips_df, zones_df, geo_df
    """
    trips_df = load_trip_data()
    zones_df = load_zone_lookup()
    geo_df = load_geojson_zones()
    return trips_df, zones_df, geo_df
