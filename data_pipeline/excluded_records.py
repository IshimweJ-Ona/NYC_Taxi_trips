"""
Export and validate all excluded data to new folder cleaned_data
"""

import pandas as pd
from pathlib import Path


OUTPUT_DIR = Path("cleaned_data")
OUTPUT_FILE = OUTPUT_DIR / "excluded_records.csv"


def merge_exclude_records(excluded_clean_df: pd.DataFrame,
                          excluded_engineered_df: pd.DataFrame):
    """
    Merge all excluded records from different pipeline stages
    and saves into one single csv file.
    """

    frames = []

    if excluded_clean_df is not None and not excluded_clean_df.empty:
        excluded_clean_df["pipeline_stage"] = "cleaning"
        frames.append(excluded_clean_df)

    if excluded_engineered_df is not None and not excluded_engineered_df.empty:
        excluded_engineered_df["pipeline_stage"] = "feature_engineering"
        frames.append(excluded_engineered_df)

    if not frames:
        print("! No excluded records.")
        return None
    
    final_df = pd.concat(frames, ignore_index=True)
    return final_df
