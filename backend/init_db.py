import os
import sys
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'logs', 'db_init.log')),
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
            
            with open(csv_path, 'r') as f:
                next(f)
                
                insert_sql = """
                INSERT INTO trips (
                    pickup_datetime, dropoff_datetime,
                    pickup_latitude, pickup_longitude,
                    dropoff_latitude, dropoff_longitude,
                    trip_distance_km, trip_duration_sec, haversine_distance_km,
                    fare_amount, tip_amount,
                    avg_speed_kmh, fare_per_km,
                    pickup_hour, pickup_weekday, is_weekend, is_peak_hour,
                    idle_time_ratio, trip_efficiency,
                    payment_type_id, passenger_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                for i, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                        
                    try:
                        values = line.strip().split(',')
                        
                        payment_type = values[11].strip('"')
                        payment_type_id = self._map_payment_type(payment_type)
                        
                        row_data = (
                            values[0].strip('"'),
                            values[1].strip('"'),
                            float(values[2]),
                            float(values[3]),
                            float(values[4]),
                            float(values[5]),
                            float(values[6]),
                            float(values[7]),
                            float(values[16]),
                            float(values[8]),
                            float(values[9]),
                            float(values[12]),
                            float(values[13]),
                            int(values[14]),
                            int(values[15]),
                            int(values[16]),
                            int(values[19]),
                            float(values[17]),
                            float(values[18]),
                            payment_type_id,
                            int(float(values[10]))
                        )
                        
                        self.cursor.execute(insert_sql, row_data)
                        
                        if i % 1000 == 0:
                            logging.info(f"Processed {i} rows...")
                            
                    except (ValueError, IndexError) as e:
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

def init_database():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, 'database', 'nyc_taxi.db')
        schema_path = os.path.join(base_dir, 'database', 'schema.sql')
        cleaned_data_path = os.path.join(base_dir, 'data', 'processed', 'cleaned_trips.csv')
        
        with DatabaseManager(db_path) as db:
            logging.info("Creating database schema...")
            if not db.execute_script_file(schema_path):
                raise Exception("Failed to create database schema")
            
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
