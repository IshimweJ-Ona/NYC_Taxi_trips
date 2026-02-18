# Backend Guide

This document explains the architecture, structure, and usage of the project's **Backend** system, which processes data requests from the frontend and serves the NYC Taxi trip insights.

## Overview
The backend is built with **Python** using the **Flask** framework. It acts as the bridge between the processed data (stored in SQLite) and the client-side user interface. It handles API requests, executes efficient SQL queries, and implements required manual algorithms.

## Infrastructure Structure

```
backend/
├── app.py              # Main entry point (Server & Config)
├── api.py              # Route definitions & Logic 
├── database.py         # Database connection helper
├── algorithms.py       # Manual algorithm implementations (Bubble Sort, etc.)
├── init_db.py          # Database initialization script
└── requirements.txt    # Python dependencies
```

## Key Components

### 1. API Server (`app.py` & `api.py`)
- **Framework**: Flask is used for its lightweight nature.
- **Blueprints**: The `api.py` file defines a discrete "Blueprint" for all API routes, keeping `app.py` clean.
- **RESTful Endpoints**:
    - `GET /api/trips`: Returns paginated trip data. Supports filtering by date, distance, fare, etc.
    - `GET /api/summary`: Aggregates statistics (Total trips, Avg Fare, etc.) based on active filters.
    - `GET /api/heatmap`: Provides geolocation data for visualization.
- **Swagger Documentation**: Integrated with `Flasgger` to provide interactive API docs at `/apidocs`.

### 2. Database (`database/nyc_taxi.db`)
- **Technology**: SQLite (perfect for this scale of embedded analytics).
- **Schema**: Defined in `database/schema.sql`.
- **Optimization**: The `init_db.py` script creates indexes on high-traffic columns (e.g., `pickup_datetime`, `fare_amount`) to ensure sub-second query performance.

### 3. Custom Algorithms (`algorithms.py`)
To meet specific assignment requirements, we implemented manual versions of standard algorithms:
- **Bubble Sort**: Manually sorts trips by fare amount when the user checks "Use Custom Algo".
- **Distance Filter**: A manual range filtering implementation.
These demonstrate algorithmic understanding without relying solely on Python's built-in `sort()` or SQL's `ORDER BY`.

## How It Works

1. **Initialization**:
   - `init_db.py` reads the processed CSV (`data/processed/cleaned_trips.csv`) and bulk-loads it into the SQLite database.
   
2. **Request Flow**:
   - **Frontend** calls `GET /api/trips?page=1&min_distance=5`.
   - **Backend** (`api.py`) parses these parameters.
   - SQL Query is dynamically built to filter results efficiently.
   - If "Custom Sort" is requested, the backend fetches *all* matching records and sorts them in-memory using `algorithms.py`.
   - Data is returned as JSON.

## Setup Instructions

1. **Environment**:
 Ensure your virtual environment is active:
 ```bash
 source venv/bin/activate  # Linux/Mac
 # or
 .\venv\Scripts\activate   # Windows
 ```

2. **Dependencies**:
 ```bash
 pip install -r backend/requirements.txt
 ```

3. **Initialize Database**:
 ```bash
 python backend/init_db.py
 ```
 *This creates the `nyc_taxi.db` file and populates it with your processed data.*

4. **Running the Server**:
 ```bash
 python backend/app.py
 ```
 The API will be available at `http://127.0.0.1:5000`.
 - Interactive Docs: `http://127.0.0.1:5000/apidocs`
