#!/usr/bin/env python3
import csv
import os
import sys
import logging
from datetime import datetime
from math import radians, sin, cos, asin, sqrt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_cleaning.log'),
        logging.StreamHandler()
    ]
)

# Constants
RAW_DEFAULT = os.path.join("data", "raw", "train_10k.csv")
OUT_DEFAULT = os.path.join("data", "cleaned_data.csv")
LOG_FILE = os.path.join("data", "logs", "data_cleaning.log")

# NYC bounding box coordinates (approximate)
NYC_MIN_LAT, NYC_MAX_LAT = 40.4774, 40.9176
NYC_MIN_LON, NYC_MAX_LON = -74.2591, -73.7004

# Expected columns in the output
dtype_mapping = {
    'pickup_datetime': str,
    'dropoff_datetime': str,
    'pickup_lat': float,
    'pickup_lon': float,
    'dropoff_lat': float,
    'dropoff_lon': float,
    'trip_distance_km': float,
    'trip_duration_sec': float,
    'fare_amount': float,
    'tip_amount': float,
    'passenger_count': int,
    'payment_type': str,
    'avg_speed_kmh': float,
    'fare_per_km': float,
    'pickup_hour': int,
    'weekday': int,
    'is_weekend': int,
    'haversine_km': float,
    'idle_time_ratio': float,  # New: Ratio of idle time to total trip time
    'trip_efficiency': float,  # New: Ratio of haversine distance to actual distance
    'is_peak_hour': int       # New: 1 if during peak hours (7-10 AM or 4-7 PM), 0 otherwise
}

def setup_logging():
    """Set up logging configuration"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth."""
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError) as e:
        logging.warning(f"Invalid coordinate values: {e}")
        return None
        
    # Earth radius in km
    R = 6371.0
    try:
        phi1, phi2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
        c = 2 * asin(sqrt(a))
        return R * c
    except ValueError as e:
        logging.warning(f"Error in haversine calculation: {e}")
        return None

def is_valid_coordinate(lat, lon):
    """Check if coordinates are within NYC bounds."""
    if lat is None or lon is None:
        return False
    return (NYC_MIN_LAT <= lat <= NYC_MAX_LAT and 
            NYC_MIN_LON <= lon <= NYC_MAX_LON)

def parse_dt(dt_str):
    """Parse datetime string into datetime object."""
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError) as e:
        logging.warning(f"Invalid datetime format: {dt_str}, error: {e}")
        return None

def calculate_features(row):
    """Calculate derived features for a trip."""
    try:
        # Parse datetimes
        pickup_dt = parse_dt(row.get('pickup_datetime'))
        dropoff_dt = parse_dt(row.get('dropoff_datetime'))
        
        # Calculate trip duration in seconds
        if pickup_dt and dropoff_dt:
            duration = (dropoff_dt - pickup_dt).total_seconds()
            if duration <= 0:
                logging.warning(f"Invalid trip duration: {duration} seconds")
                return None
        else:
            logging.warning("Missing pickup or dropoff datetime")
            return None
        
        # Get coordinates
        try:
            pickup_lat = float(row.get('pickup_latitude', 0))
            pickup_lon = float(row.get('pickup_longitude', 0))
            dropoff_lat = float(row.get('dropoff_latitude', 0))
            dropoff_lon = float(row.get('dropoff_longitude', 0))
        except (TypeError, ValueError) as e:
            logging.warning(f"Invalid coordinate values: {e}")
            return None
            
        # Validate coordinates
        if not all([is_valid_coordinate(pickup_lat, pickup_lon),
                   is_valid_coordinate(dropoff_lat, dropoff_lon)]):
            logging.warning("Coordinates outside NYC bounds")
            return None
            
        # Calculate haversine distance
        haversine_dist = haversine_km(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon
        )
        
        if haversine_dist is None:
            return None
            
        # Get trip distance (converting miles to km if needed)
        try:
            trip_distance_km = float(row.get('trip_distance', 0)) * 1.60934  # Convert miles to km
        except (TypeError, ValueError):
            trip_distance_km = 0
            
        # Calculate average speed (km/h)
        avg_speed_kmh = (trip_distance_km / duration) * 3600 if duration > 0 else 0
        
        # Calculate fare per km
        try:
            fare_amount = float(row.get('fare_amount', 0))
            fare_per_km = fare_amount / trip_distance_km if trip_distance_km > 0 else 0
        except (TypeError, ValueError):
            fare_per_km = 0
            
        # Calculate derived features
        pickup_hour = pickup_dt.hour
        weekday = pickup_dt.weekday()  # Monday is 0, Sunday is 6
        is_weekend = 1 if weekday >= 5 else 0
        
        # New feature: Idle time ratio (time not moving / total time)
        idle_time_ratio = 1 - (haversine_dist / (trip_distance_km or 1))
        idle_time_ratio = max(0, min(1, idle_time_ratio))  # Clamp between 0 and 1
        
        # New feature: Trip efficiency (straight-line distance / actual distance)
        trip_efficiency = haversine_dist / (trip_distance_km or 1)
        
        # New feature: Peak hour indicator (7-10 AM or 4-7 PM on weekdays)
        is_peak_hour = 1 if (not is_weekend and 
                            ((7 <= pickup_hour < 10) or (16 <= pickup_hour < 19))) else 0
        
        # Create cleaned row
        cleaned_row = {
            'pickup_datetime': row.get('pickup_datetime', ''),
            'dropoff_datetime': row.get('dropoff_datetime', ''),
            'pickup_lat': pickup_lat,
            'pickup_lon': pickup_lon,
            'dropoff_lat': dropoff_lat,
            'dropoff_lon': dropoff_lon,
            'trip_distance_km': trip_distance_km,
            'trip_duration_sec': duration,
            'fare_amount': fare_amount,
            'tip_amount': float(row.get('tip_amount', 0)),
            'passenger_count': int(float(row.get('passenger_count', 1))),
            'payment_type': row.get('payment_type', ''),
            'avg_speed_kmh': avg_speed_kmh,
            'fare_per_km': fare_per_km,
            'pickup_hour': pickup_hour,
            'weekday': weekday,
            'is_weekend': is_weekend,
            'haversine_km': haversine_dist,
            'idle_time_ratio': idle_time_ratio,
            'trip_efficiency': trip_efficiency,
            'is_peak_hour': is_peak_hour
        }
        
        return cleaned_row
        
    except Exception as e:
        logging.error(f"Error processing row: {e}", exc_info=True)
        return None

def clean(raw_path=RAW_DEFAULT, out_path=OUT_DEFAULT):
    """Main function to clean and process the raw data."""
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Initialize counters
    total_rows = 0
    valid_rows = 0
    
    try:
        with open(raw_path, 'r', encoding='utf-8') as infile, \
             open(out_path, 'w', newline='', encoding='utf-8') as outfile:
            
            # Initialize CSV reader and writer
            reader = csv.DictReader(infile)
            
            # Write header
            fieldnames = list(dtype_mapping.keys())
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Process each row
            for row in reader:
                total_rows += 1
                
                # Clean and process the row
                cleaned_row = calculate_features(row)
                
                # Write valid rows to output
                if cleaned_row:
                    writer.writerow(cleaned_row)
                    valid_rows += 1
                
                # Log progress
                if total_rows % 1000 == 0:
                    logging.info(f"Processed {total_rows} rows...")
            
            # Log summary
            logging.info(f"Processing complete. Processed {total_rows} rows, {valid_rows} valid rows written to {out_path}")
            logging.info(f"Data quality: {valid_rows / total_rows * 100:.2f}% of rows passed validation")
            
    except Exception as e:
        logging.error(f"Error processing file: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    setup_logging()
    sys.exit(clean())
