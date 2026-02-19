import os
import sys
import sqlite3
import logging
import csv
import json
from datetime import datetime

# Ensure log directory exists
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(base_dir, 'data', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'db_init.log')),
        logging.StreamHandler()
    ]
)

class DatabaseManager:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, 'data', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.cursor.execute('PRAGMA foreign_keys = ON;')
            logging.info(f"Connected to database at {self.db_path}")
        except sqlite3.Error as e:
            logging.error(f"Error connecting to database: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()
            logging.info("Database connection closed")

    def execute_script_file(self, script_path):
        try:
            with open(script_path, 'r') as f:
                sql_script = f.read()
            self.cursor.executescript(sql_script)
            self.conn.commit()
            logging.info(f"Executed SQL script: {script_path}")
            return True
        except (sqlite3.Error, IOError) as e:
            logging.error(f"Error executing script {script_path}: {e}")
            self.conn.rollback()
            return False

    def load_cleaned_data(self, csv_path):
        if not os.path.exists(csv_path):
            logging.error(f"CSV file not found: {csv_path}")
            return False

        try:
            self.cursor.execute('BEGIN TRANSACTION;')
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                insert_sql = """
                INSERT INTO trips (
                    pickup_datetime, dropoff_datetime,
                    pu_location_id, do_location_id,
                    pickup_latitude, pickup_longitude,
                    dropoff_latitude, dropoff_longitude,
                    trip_distance_km, trip_duration_sec, haversine_distance_km,
                    fare_amount, tip_amount,
                    avg_speed_kmh, fare_per_km,
                    pickup_hour, pickup_weekday, is_weekend, is_peak_hour,
                    idle_time_ratio, trip_efficiency,
                    payment_type_id, passenger_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                for i, row in enumerate(reader, 1):
                    if not row:
                        continue
                    
                    try:
                        pickup_dt = self._get(row, ["pickup_datetime", "tpep_pickup_datetime"])
                        dropoff_dt = self._get(row, ["dropoff_datetime", "tpep_dropoff_datetime"])
                        
                        pu_location_id = self._parse_int(self._get(row, ["pu_location_id", "pulocationid"]))
                        do_location_id = self._parse_int(self._get(row, ["do_location_id", "dolocationid"]))
                        
                        pickup_lat = self._parse_float(self._get(row, ["pickup_latitude", "pickup_lat"]))
                        pickup_lon = self._parse_float(self._get(row, ["pickup_longitude", "pickup_lon", "pickup_lng"]))
                        dropoff_lat = self._parse_float(self._get(row, ["dropoff_latitude", "dropoff_lat"]))
                        dropoff_lon = self._parse_float(self._get(row, ["dropoff_longitude", "dropoff_lon", "dropoff_lng"]))
                        
                        trip_distance_km = self._parse_float(self._get(row, ["trip_distance_km"]))
                        if trip_distance_km is None:
                            dist_miles = self._parse_float(self._get(row, ["trip_distance", "distance"]))
                            trip_distance_km = dist_miles * 1.60934 if dist_miles is not None else None
                        
                        trip_duration_sec = self._parse_int(self._get(row, ["trip_duration_sec"]))
                        if trip_duration_sec is None:
                            duration_min = self._parse_float(self._get(row, ["trip_duration_minutes", "trip_duration_min"]))
                            trip_duration_sec = int(duration_min * 60) if duration_min is not None else None
                        
                        haversine_km = self._parse_float(self._get(row, ["haversine_distance_km", "haversine_km"]))
                        fare_amount = self._parse_float(self._get(row, ["fare_amount", "fare"]))
                        tip_amount = self._parse_float(self._get(row, ["tip_amount", "tip"])) or 0.0
                        avg_speed_kmh = self._parse_float(self._get(row, ["avg_speed_kmh", "average_speed_kmh"]))
                        fare_per_km = self._parse_float(self._get(row, ["fare_per_km", "revenue_per_km"]))
                        
                        pickup_hour = self._parse_int(self._get(row, ["pickup_hour"]))
                        pickup_weekday = self._parse_int(self._get(row, ["pickup_weekday", "weekday"]))
                        if pickup_weekday is None and pickup_dt:
                            pickup_weekday = self._parse_datetime(pickup_dt).weekday()
                        
                        is_weekend = self._parse_int(self._get(row, ["is_weekend"]))
                        if is_weekend is None and pickup_weekday is not None:
                            is_weekend = 1 if pickup_weekday >= 5 else 0
                        
                        is_peak_hour = self._parse_int(self._get(row, ["is_peak_hour"]))
                        
                        idle_time_ratio = self._parse_float(self._get(row, ["idle_time_ratio"]))
                        trip_efficiency = self._parse_float(self._get(row, ["trip_efficiency"]))
                        
                        payment_type = self._get(row, ["payment_type", "payment"])
                        payment_type_id = self._map_payment_type(payment_type)
                        passenger_count = self._parse_int(self._get(row, ["passenger_count", "passengers"])) or 0
                        
                        row_data = (
                            pickup_dt,
                            dropoff_dt,
                            pu_location_id,
                            do_location_id,
                            pickup_lat,
                            pickup_lon,
                            dropoff_lat,
                            dropoff_lon,
                            trip_distance_km,
                            trip_duration_sec,
                            haversine_km,
                            fare_amount,
                            tip_amount,
                            avg_speed_kmh,
                            fare_per_km,
                            pickup_hour,
                            pickup_weekday,
                            is_weekend,
                            is_peak_hour,
                            idle_time_ratio,
                            trip_efficiency,
                            payment_type_id,
                            passenger_count
                        )
                        
                        self.cursor.execute(insert_sql, row_data)
                        
                        if i % 1000 == 0:
                            logging.info(f"Processed {i} rows...")
                            
                    except (ValueError, IndexError, AttributeError) as e:
                        logging.warning(f"Skipping malformed row {i}: {e}")
                        continue
                        
            self.conn.commit()
            logging.info(f"Successfully loaded data from {csv_path}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error loading data: {e}", exc_info=True)
            return False

    def _map_payment_type(self, payment_type):
        payment_map = {
            '1': 1,
            'CRD': 1,
            '2': 2,
            'CSH': 2,
            '3': 3,
            'NOC': 3,
            '4': 4,
            'DIS': 4,
            '5': 5,
            'UNK': 5,
            '6': 6 
        }
        return payment_map.get(str(payment_type).upper().strip('"'), 5)

    def _get(self, row, names):
        for name in names:
            if name in row and row[name] not in (None, "", "\\N"):
                return row[name]
        return None

    def _parse_float(self, value):
        try:
            return float(value) if value not in (None, "", "\\N") else None
        except Exception:
            return None

    def _parse_int(self, value):
        try:
            return int(float(value)) if value not in (None, "", "\\N") else None
        except Exception:
            return None

    def _parse_datetime(self, value):
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(str(value), fmt)
                except Exception:
                    pass
        return None

    def load_zones(self, csv_path):
        if not os.path.exists(csv_path):
            logging.warning(f"Zones CSV not found: {csv_path}")
            return False
        
        try:
            self.cursor.execute('BEGIN TRANSACTION;')
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                insert_sql = """
                INSERT OR REPLACE INTO zones (
                    location_id, borough, zone, service_zone
                ) VALUES (?, ?, ?, ?)
                """
                
                for i, row in enumerate(reader, 1):
                    location_id = self._parse_int(self._get(row, ["locationid", "location_id"]))
                    if location_id is None:
                        continue
                    borough = self._get(row, ["borough"])
                    zone = self._get(row, ["zone"])
                    service_zone = self._get(row, ["service_zone", "servicezone"])
                    self.cursor.execute(insert_sql, (location_id, borough, zone, service_zone))
                    
                    if i % 500 == 0:
                        logging.info(f"Inserted {i} zones...")
            
            self.conn.commit()
            logging.info(f"Loaded zones from {csv_path}")
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error loading zones: {e}", exc_info=True)
            return False

    def load_zones_geo(self, geojson_path):
        if not os.path.exists(geojson_path):
            logging.warning(f"Zones GeoJSON not found: {geojson_path}")
            return False
        
        try:
            self.cursor.execute('BEGIN TRANSACTION;')
            with open(geojson_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get("features", [])
            insert_sql = """
            INSERT OR REPLACE INTO zones_geo (
                location_id, borough, zone, service_zone, geometry
            ) VALUES (?, ?, ?, ?, ?)
            """
            
            for i, feature in enumerate(features, 1):
                props = feature.get("properties", {})
                geom = feature.get("geometry")
                location_id = self._parse_int(props.get("locationid"))
                if location_id is None:
                    continue
                borough = props.get("borough")
                zone = props.get("zone")
                service_zone = props.get("service_zone") or props.get("servicezone")
                self.cursor.execute(insert_sql, (location_id, borough, zone, service_zone, json.dumps(geom)))
                
                if i % 200 == 0:
                    logging.info(f"Inserted {i} zone geometries...")
            
            self.conn.commit()
            logging.info(f"Loaded zone geometries from {geojson_path}")
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error loading zone geometries: {e}", exc_info=True)
            return False

def init_database():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, 'database', 'nyc_taxi.db')
        schema_path = os.path.join(base_dir, 'database', 'schema.sql')
        cleaned_data_path = os.path.join(base_dir, 'data', 'processed', 'cleaned_trips.csv')
        zones_path = os.path.join(base_dir, 'data', 'processed', 'zones_cleaned.csv')
        zones_geo_path = os.path.join(base_dir, 'data', 'processed', 'zones_geo_cleaned.geojson')
        
        with DatabaseManager(db_path) as db:
            logging.info("Creating database schema...")
            if not db.execute_script_file(schema_path):
                raise Exception("Failed to create database schema")
            
            logging.info("Loading zones...")
            db.load_zones(zones_path)
            db.load_zones_geo(zones_geo_path)
            
            logging.info("Loading cleaned data...")
            if not db.load_cleaned_data(cleaned_data_path):
                raise Exception("Failed to load cleaned data")
            
            logging.info("Creating additional indexes...")
            db.cursor.executescript("""
                CREATE INDEX IF NOT EXISTS idx_trips_payment_type 
                ON trips(payment_type_id);
                
                CREATE INDEX IF NOT EXISTS idx_trips_weekday_hour 
                ON trips(pickup_weekday, pickup_hour);
                
                CREATE INDEX IF NOT EXISTS idx_trips_fare_per_km 
                ON trips(fare_per_km);
            """)
            db.conn.commit()
            
            logging.info("Optimizing database...")
            db.cursor.execute("VACUUM;")
            
            logging.info("Database initialization completed successfully!")
            return True
            
    except Exception as e:
        logging.error(f"Database initialization failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logging.info("Starting database initialization...")
    if init_database():
        logging.info("Database setup completed successfully!")
    else:
        logging.error("Database setup failed. Check the logs for details.")
        sys.exit(1)
