"""
Remove missing & Invalid records
Remove duplicates
Join zone lookup (PU & DO)
Track excluded records and provide the reason for exclusion
"""

import pandas as pd
from pandas import DataFrame
from typing import Tuple


def clean_trip_data(trips_df: pd.DataFrame, zones_df: pd.DataFrame)-> Tuple[DataFrame, DataFrame]:
    """Clean raw trip data by:
        - removing missing values
        - removing invalid/outlieer records
        - removing duplicates
        - joining zone lookup data
        - tracking excluded records with reasons
    """

    excluded_records = []

    df = trips_df.copy()

    # Handle missing values
    essential_cols = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "trip_distance",
        "total_amount",
        "pulocationid",
        "dolocationid"
    ]

    missing_mask = df[essential_cols].isnull().any(axis=1)
    missing_rows = df[missing_mask].copy()
    missing_rows["exclusion_reason"] = "missing_essential_values"
    excluded_records.append(missing_rows)

    df = df[~missing_mask]

    # Remove invalid logical records
    invalid_mask = (
        (df["trip_distance"] <= 0) |
        (df["total_amount"] < 0) |
        (df["fare_amount"] < 0) |
        (df["passenger_count"] <= 0) |
        (df["tpep_dropoff_datetime"] <= df["tpep_pickup_datetime"])
    )

    invalid_rows = df[invalid_mask].copy()
    invalid_rows["exclusion_reason"] = "invalid_logical_values"
    excluded_records.append(invalid_rows)

    df = df[~invalid_mask]

    # Remove duplicates
    duplicate_mask = df.duplicated(subset=[
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "pulocationid",
        "dolocationid"
    ])

    duplicate_rows = df[duplicate_mask].copy()
    duplicate_rows["exclusion_reason"] = "duplicate_trip"
    excluded_records.append(duplicate_rows)

    df = df[~duplicate_mask]

    # Join zone lookup table
    zones_df = zones_df.rename(columns={
        "locationid": "zone_locationid",
        "borough": "zone_borough",
        "zone": "zone_name"
    })

    # pickup zone join
    df = df.merge(
        zones_df,
        how="left",
        left_on="pulocationid",
        right_on="zone_locationid"
    )

    # dropoff zone join
    df = df.merge(
        zones_df,
        how="left",
        left_on="dolocationid",
        right_on="zone_locationid",
        suffixes=("_pickup", "_dropoff")
    )

    df = df.rename(columns={
        "zone_borough_pickup": "pickup_borough",
        "zone_name_pickup": "pickup_zone",
        "zone_borough_dropoff": "dropoff_borough",
        "zone_name_dropoff": "dropoff_zone"
    })

    df = df.drop(columns=["zone_locationid", "service_zone"], errors="ignore")

    # Handle unmatched zones
    unmatched_mask = df["pickup_zone"].isnull() | df["dropoff_zone"].isnull()
    unmatched_rows = df[unmatched_mask].copy()
    unmatched_rows["exclusion_reason"] = "unmatched_zone_lookup"
    excluded_records.append(unmatched_rows)

    df = df[~unmatched_mask]

    # Normalize categorical columns
    df["store_and_fwd_flag"] = df["store_and_fwd_flag"].str.upper()
    df["pickup_borough"] = df["pickup_borough"].str.title()
    df["dropoff_borough"] = df["dropoff_borough"].str.title()

    # Combine excluded records
    excluded_df = pd.concat(excluded_records, ignore_index=True)

    print(f"Cleaned trips shape: {df.shape}")
    print(f"Excluded records: {excluded_df.shape}")

    return df, excluded_df

