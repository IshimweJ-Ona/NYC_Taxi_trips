import pandas as pd
from pathlib import Path


RAW_DIR = Path("data/raw")
PARQUET_DIR = Path("data/parquet")

PARQUET_DIR.mkdir(parents=True, exist_ok=True)

# Convert trip data
trip_csv = RAW_DIR / "yellow_tripdata_2019-01.csv"
trip_parquet = PARQUET_DIR / "yellow_tripdata_2019-01.parquet"

df_trips = pd.read_csv(trip_csv)
df_trips.to_parquet(trip_parquet, index=False)

print("** Trip data converted to Parquet **")

# Convert zone lookup
zone_csv = RAW_DIR / "taxi_zone_lookup.csv"
zone_parquet = PARQUET_DIR / "taxi_zone_lookup.parquet"

df_zones = pd.read_csv(zone_csv)
df_zones.to_parquet(zone_parquet, index=False)

print("** Taxi zone lookup converted to Parquet **")
