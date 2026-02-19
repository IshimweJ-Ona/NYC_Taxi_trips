DROP TABLE IF EXISTS trips;

DROP TABLE IF EXISTS payment_types;
DROP TABLE IF EXISTS zones_geo;
DROP TABLE IF EXISTS zones;

CREATE TABLE payment_types (
    payment_type_id INTEGER PRIMARY KEY,
    payment_type_name TEXT NOT NULL
);

INSERT INTO
    payment_types (
        payment_type_id,
        payment_type_name
    )
VALUES (1, 'Credit Card'),
    (2, 'Cash'),
    (3, 'No Charge'),
    (4, 'Dispute'),
    (5, 'Unknown'),
    (6, 'Voided Trip');

CREATE TABLE zones (
    location_id INTEGER PRIMARY KEY,
    borough TEXT,
    zone TEXT,
    service_zone TEXT
);

CREATE TABLE zones_geo (
    location_id INTEGER PRIMARY KEY,
    borough TEXT,
    zone TEXT,
    service_zone TEXT,
    geometry TEXT
);

CREATE TABLE trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pickup_datetime TEXT NOT NULL,
    dropoff_datetime TEXT NOT NULL,
    pu_location_id INTEGER,
    do_location_id INTEGER,
    pickup_latitude REAL,
    pickup_longitude REAL,
    dropoff_latitude REAL,
    dropoff_longitude REAL,
    trip_distance_km REAL CHECK (trip_distance_km >= 0),
    trip_duration_sec INTEGER CHECK (trip_duration_sec > 0),
    haversine_distance_km REAL,
    fare_amount REAL CHECK (fare_amount >= 0),
    tip_amount REAL CHECK (tip_amount >= 0),
    avg_speed_kmh REAL CHECK (avg_speed_kmh >= 0),
    fare_per_km REAL,
    pickup_hour INTEGER CHECK (pickup_hour BETWEEN 0 AND 23),
    pickup_weekday INTEGER CHECK (
        pickup_weekday BETWEEN 0 AND 6
    ),
    is_weekend INTEGER,
    is_peak_hour INTEGER,
    idle_time_ratio REAL,
    trip_efficiency REAL,
    payment_type_id INTEGER,
    passenger_count INTEGER CHECK (passenger_count >= 0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_type_id) REFERENCES payment_types (payment_type_id),
    FOREIGN KEY (pu_location_id) REFERENCES zones (location_id),
    FOREIGN KEY (do_location_id) REFERENCES zones (location_id)
);

CREATE INDEX idx_trips_pickup_time ON trips (pickup_datetime);

CREATE INDEX idx_trips_dropoff_time ON trips (dropoff_datetime);

CREATE INDEX idx_trips_pu_location ON trips (pu_location_id);

CREATE INDEX idx_trips_do_location ON trips (do_location_id);

CREATE INDEX idx_trips_pickup_loc ON trips (
    pickup_latitude,
    pickup_longitude
);

CREATE INDEX idx_trips_dropoff_loc ON trips (
    dropoff_latitude,
    dropoff_longitude
);

CREATE INDEX idx_trips_speed ON trips (avg_speed_kmh);

CREATE INDEX idx_trips_fare ON trips (fare_amount);