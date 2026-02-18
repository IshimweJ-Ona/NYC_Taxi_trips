import os
import sqlite3

def get_conn():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_path = os.path.join(base_dir, "database", "nyc_taxi.db")
    
    db_path = os.getenv("SQLITE_PATH", default_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
