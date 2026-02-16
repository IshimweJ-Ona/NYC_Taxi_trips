"""
Move all expensivie.heavy operations into preprocessing stage so
that backend only performs simple databses queries, improving system performance
"""

import pandas as pd
from pandas import DataFrame
from typing import Tuple

def engineer_features(clean_df: pd.DataFrame)-> Tuple[DataFrame, DataFrame]:
    """Adds:
         -trip_duration_minutes
         - avarage_speed_kmh
         -revenue_per_km
         -pickup_hour
         -pickup_day
         -is_peak_hour
        Removes invalid engineering rows and logs exclusions.
    """

    excluded_records = []

    df = clean_df.copy()

    # Trip durations(minutes)
    df["trip_duration_minutes"] = (
        (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"])
        .dt.total_seconds() /60
    )

    invalid_duration_mask = df["trip_duration_minutes"] <= 0
    bad_duration = df[invalid_duration_mask].copy()
    bad_duration["exclusion_reason"] = "invalid_trip_duration"
    excluded_records.append(bad_duration)

    df = df[~invalid_duration_mask]

    # Avarage speed (km/h)
    df["average_speed_kmh"] = df["trip_distance"] / (df["trip_duration_minutes"] / 60)

    invalid_speed_mask = (df["average_speed_kmh"] <= 0) | (df["average_speed_kmh"] > 150)
    bad_speed = df[invalid_speed_mask].copy()
    bad_speed["exclusion_reason"] = "invalid_average_speed"
    excluded_records.append(bad_speed)

    df = df[~invalid_speed_mask]

    # Revenue per km
    df["revenue_per_km"] = df["total_amount"] / df["trip_distance"]

    invalid_revenue_mask = df["revenue_per_km"] <= 0
    bad_revenue = df[invalid_revenue_mask].copy()
    bad_revenue["exclusion_reason"] = "invalid_revenue_per_km"
    excluded_records.append(bad_revenue)

    df = df[~invalid_revenue_mask]

    # Time based features
    df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
    df["pickup_day"] = df["tpep_pickup_datetime"].dt.day_name()

    # Peak hour: 7-10 AM and 4-7 PM
    df["is_peak_hour"] = df["pickup_hour"].apply(
        lambda x: 1 if (7 <= x <= 10 or 16 <= x <= 19) else 0
    )

    # Exclude records
    excluded_df = pd.concat(excluded_records, ignore_index=True)

    print(f"Feature engineered rows: {df.shape}")
    print(f"Excluded engineered rows: {excluded_df.shape}")

    return df, excluded_df
