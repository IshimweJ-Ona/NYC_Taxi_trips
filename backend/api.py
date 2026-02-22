#!/usr/bin/env python3
import os
import sqlite3
import json
import time
from threading import Lock
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from functools import wraps
from algorithms import manual_merge_sort_trips

api = Blueprint('api', __name__)
_CACHE_LOCK = Lock()
_RESPONSE_CACHE = {}


def _cache_key(prefix):
    pairs = []
    for key in request.args.keys():
        values = request.args.getlist(key)
        idx = 0
        while idx < len(values):
            pairs.append((key, values[idx]))
            idx += 1
    pairs.sort(key=lambda item: (item[0], item[1]))
    return f"{prefix}:{json.dumps(pairs, separators=(',', ':'))}"


def _cache_get(key):
    now = time.time()
    with _CACHE_LOCK:
        record = _RESPONSE_CACHE.get(key)
        if not record:
            return None
        expires_at, payload = record
        if expires_at <= now:
            _RESPONSE_CACHE.pop(key, None)
            return None
        return payload


def _cache_set(key, payload, ttl_seconds):
    expires_at = time.time() + ttl_seconds
    with _CACHE_LOCK:
        _RESPONSE_CACHE[key] = (expires_at, payload)


def _filters_cache_key(prefix, filters):
    items = []
    for key in filters:
        items.append((key, str(filters[key])))
    items.sort(key=lambda item: (item[0], item[1]))
    return f"{prefix}:{json.dumps(items, separators=(',', ':'))}"

def get_db_connection():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'database', 'nyc_taxi.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def handle_db_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlite3.Error as e:
            current_app.logger.error(f"Database error: {e}")
            return jsonify({"error": "Database error"}), 500
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    return wrapper

def parse_date(date_str, default=None):
    if not date_str:
        return default
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return default

def build_join_clause(filters):
    # Core analytics/trips endpoints do not require zone joins.
    _ = filters
    return ""

def build_where_clause(filters):
    conditions = []
    params = {}
    
    if 'start_date' in filters:
        conditions.append("DATE(t.pickup_datetime) >= :start_date")
        params['start_date'] = filters['start_date']
    if 'end_date' in filters:
        conditions.append("DATE(t.pickup_datetime) <= :end_date")
        params['end_date'] = filters['end_date']
    
    if 'pickup_lat' in filters and 'pickup_lon' in filters:
        conditions.append("""
            t.pickup_latitude BETWEEN :min_pickup_lat AND :max_pickup_lat
            AND t.pickup_longitude BETWEEN :min_pickup_lon AND :max_pickup_lon
        """)
        params.update({
            'min_pickup_lat': float(filters['pickup_lat']) - 0.01,
            'max_pickup_lat': float(filters['pickup_lat']) + 0.01,
            'min_pickup_lon': float(filters['pickup_lon']) - 0.01,
            'max_pickup_lon': float(filters['pickup_lon']) + 0.01,
        })
    
    if 'min_distance' in filters:
        conditions.append("t.trip_distance_km >= :min_distance")
        params['min_distance'] = float(filters['min_distance'])
    if 'max_distance' in filters:
        conditions.append("t.trip_distance_km <= :max_distance")
        params['max_distance'] = float(filters['max_distance'])
    
    if 'min_fare' in filters:
        conditions.append("t.fare_amount >= :min_fare")
        params['min_fare'] = float(filters['min_fare'])
    if 'max_fare' in filters:
        conditions.append("t.fare_amount <= :max_fare")
        params['max_fare'] = float(filters['max_fare'])
    
    if 'passenger_count' in filters:
        conditions.append("t.passenger_count = :passenger_count")
        params['passenger_count'] = int(filters['passenger_count'])
    
    if 'payment_type' in filters:
        conditions.append("t.payment_type_id = :payment_type")
        params['payment_type'] = int(filters['payment_type'])
    
    if 'is_peak_hour' in filters:
        conditions.append("t.is_peak_hour = :is_peak_hour")
        params['is_peak_hour'] = 1 if filters['is_peak_hour'].lower() == 'true' else 0
    
    if 'is_weekend' in filters:
        conditions.append("t.is_weekend = :is_weekend")
        params['is_weekend'] = 1 if filters['is_weekend'].lower() == 'true' else 0

    if 'pu_location_id' in filters:
        conditions.append("t.pu_location_id = :pu_location_id")
        params['pu_location_id'] = int(filters['pu_location_id'])

    if 'do_location_id' in filters:
        conditions.append("t.do_location_id = :do_location_id")
        params['do_location_id'] = int(filters['do_location_id'])

    if 'pu_location_ids' in filters:
        raw_ids = str(filters['pu_location_ids'])
        pieces = raw_ids.split(',')
        in_params = []
        index = 0
        while index < len(pieces):
            cleaned = pieces[index].strip()
            if cleaned:
                param_key = f"pu_location_id_{index}"
                params[param_key] = int(cleaned)
                in_params.append(f":{param_key}")
            index += 1
        if in_params:
            conditions.append(f"t.pu_location_id IN ({', '.join(in_params)})")

    if 'do_location_ids' in filters:
        raw_ids = str(filters['do_location_ids'])
        pieces = raw_ids.split(',')
        in_params = []
        index = 0
        while index < len(pieces):
            cleaned = pieces[index].strip()
            if cleaned:
                param_key = f"do_location_id_{index}"
                params[param_key] = int(cleaned)
                in_params.append(f":{param_key}")
            index += 1
        if in_params:
            conditions.append(f"t.do_location_id IN ({', '.join(in_params)})")

    # Zone/borough filters are resolved in the frontend into location-id filters.
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


def query_summary_payload(filters):
    where_clause, params = build_where_clause(filters)

    with get_db_connection() as conn:
        query = f"""
            SELECT
                COUNT(*) as total_trips,
                COALESCE(AVG(trip_distance_km), 0) as avg_distance_km,
                COALESCE(AVG(fare_amount), 0) as avg_fare,
                COALESCE(AVG(tip_amount), 0) as avg_tip,
                COALESCE(AVG(tip_amount / NULLIF(fare_amount, 0)) * 100, 0) as avg_tip_percentage,
                COALESCE(AVG(avg_speed_kmh), 0) as avg_speed_kmh,
                COALESCE(AVG(fare_per_km), 0) as avg_fare_per_km,
                COALESCE(AVG(trip_efficiency), 0) as avg_efficiency,
                SUM(CASE WHEN is_peak_hour = 1 THEN 1 ELSE 0 END) as peak_hour_trips,
                SUM(CASE WHEN is_weekend = 1 THEN 1 ELSE 0 END) as weekend_trips
            FROM trips t
            WHERE {where_clause}
        """
        result = conn.execute(query, params).fetchone()

        payment_query = f"""
            SELECT p.payment_type_name, COUNT(*) as count
            FROM trips t
            JOIN payment_types p ON t.payment_type_id = p.payment_type_id
            WHERE {where_clause}
            GROUP BY p.payment_type_name
            ORDER BY count DESC
        """
        payment_dist = [dict(row) for row in conn.execute(payment_query, params)]

        hourly_query = f"""
            SELECT
                pickup_hour,
                COUNT(*) as trip_count,
                COALESCE(AVG(fare_amount), 0) as avg_fare,
                COALESCE(AVG(tip_amount), 0) as avg_tip
            FROM trips t
            WHERE {where_clause}
            GROUP BY pickup_hour
            ORDER BY pickup_hour
        """
        hourly_data = [dict(row) for row in conn.execute(hourly_query, params)]

    summary = dict(result)
    # Friendly aliases for clients.
    summary["avg_distance"] = summary.get("avg_distance_km", 0)
    summary["avg_speed"] = summary.get("avg_speed_kmh", 0)
    summary["payment_distribution"] = payment_dist
    summary["hourly_distribution"] = hourly_data
    return summary


def query_trips_payload(filters, page, per_page, sort, order, use_custom_sort):
    offset = (page - 1) * per_page
    where_clause, params = build_where_clause(filters)
    join_clause = build_join_clause(filters)
    params.update({'limit': per_page, 'offset': offset})

    sort_map = {
        'pickup_datetime': 't.pickup_datetime',
        'dropoff_datetime': 't.dropoff_datetime',
        'trip_distance_km': 't.trip_distance_km',
        'fare_amount': 't.fare_amount',
        'tip_amount': 't.tip_amount',
        'avg_speed_kmh': 't.avg_speed_kmh'
    }
    sort_column = sort_map.get(sort, 't.pickup_datetime')
    # Keep pagination stable when the primary sort column has duplicate values.
    order_by = f"{sort_column} {order.upper()}, t.id {order.upper()}"

    with get_db_connection() as conn:
        count_query = f"""
            SELECT COUNT(*) as total
            FROM trips t
            {join_clause}
            WHERE {where_clause}
        """
        total = conn.execute(count_query, params).fetchone()['total']

        if use_custom_sort:
            query = f"""
                SELECT t.*, p.payment_type_name
                FROM trips t
                LEFT JOIN payment_types p ON t.payment_type_id = p.payment_type_id
                WHERE {where_clause}
            """
            all_trips = [dict(row) for row in conn.execute(query, params)]
            sorted_trips = manual_merge_sort_trips(
                all_trips,
                sort_field=sort if sort in sort_map else 'pickup_datetime',
                ascending=(order == 'asc')
            )
            trips = sorted_trips[offset:offset + per_page]
        else:
            query = f"""
                SELECT t.*, p.payment_type_name
                FROM trips t
                LEFT JOIN payment_types p ON t.payment_type_id = p.payment_type_id
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
            """
            trips = [dict(row) for row in conn.execute(query, params)]

    return {
        'data': trips,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        },
        'algorithm_used': 'Manual Merge Sort' if use_custom_sort else 'SQL Order By'
    }

@api.route('/api/trips', methods=['GET'])
@handle_db_errors
def get_trips():
    """
    Get paginated list of trips with optional filters.
    ---
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 100
        description: Items per page (max 100)
      - name: start_date
        in: query
        type: string
        format: date
        description: Filter by start date (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Filter by end date (YYYY-MM-DD)
      - name: min_distance
        in: query
        type: number
        description: Minimum trip distance in km
      - name: max_distance
        in: query
        type: number
        description: Maximum trip distance in km
      - name: min_fare
        in: query
        type: number
        description: Minimum fare amount
      - name: max_fare
        in: query
        type: number
        description: Maximum fare amount
      - name: payment_type
        in: query
        type: integer
        description: Filter by payment type ID
      - name: custom_sort
        in: query
        type: boolean
        description: Use manual bubble sort algorithm (Requirement 3)
    responses:
      200:
        description: List of trips
    """
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 100)), 100)

    cache_key = _cache_key("trips")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)
    
    filters = {k: v for k, v in request.args.items()
              if k not in ['page', 'per_page', 'sort', 'order', 'custom_sort']}

    sort = request.args.get('sort', 'pickup_datetime')
    order = request.args.get('order', 'desc').lower()
    if order not in ('asc', 'desc'):
        order = 'desc'
    use_custom_sort = request.args.get('custom_sort', 'false').lower() == 'true'
    response = query_trips_payload(filters, page, per_page, sort, order, use_custom_sort)
    _cache_set(cache_key, response, ttl_seconds=30)
    return jsonify(response)

@api.route('/api/summary', methods=['GET'])
@handle_db_errors
def get_summary():
    """
    Get summary statistics for trips.
    ---
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Filter by start date (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Filter by end date (YYYY-MM-DD)
    responses:
      200:
        description: Summary statistics
    """
    cache_key = _cache_key("summary")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    filters = dict(request.args)
    summary = query_summary_payload(filters)
    _cache_set(cache_key, summary, ttl_seconds=30)
    return jsonify(summary)


@api.route('/api/dashboard', methods=['GET'])
@handle_db_errors
def get_dashboard():
    """
    Get dashboard payload with summary metrics + paginated trip records.
    """
    cache_key = _cache_key("dashboard")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 100)), 100)
    sort = request.args.get('sort', 'pickup_datetime')
    order = request.args.get('order', 'desc').lower()
    if order not in ('asc', 'desc'):
        order = 'desc'
    use_custom_sort = request.args.get('custom_sort', 'false').lower() == 'true'
    include_summary = request.args.get('include_summary', 'true').lower() == 'true'
    include_trips = request.args.get('include_trips', 'true').lower() == 'true'
    filters = {k: v for k, v in request.args.items()
              if k not in ['page', 'per_page', 'sort', 'order', 'custom_sort', 'include_summary', 'include_trips']}

    payload = {}
    if include_trips:
        trips_payload = query_trips_payload(filters, page, per_page, sort, order, use_custom_sort)
        payload["trips"] = trips_payload

    if include_summary:
        summary_cache_key = _filters_cache_key("dashboard_summary", filters)
        summary_payload = _cache_get(summary_cache_key)
        if summary_payload is None:
            summary_payload = query_summary_payload(filters)
            _cache_set(summary_cache_key, summary_payload, ttl_seconds=30)
        payload["summary"] = summary_payload

    _cache_set(cache_key, payload, ttl_seconds=30)
    return jsonify(payload)

@api.route('/api/heatmap', methods=['GET'])
@handle_db_errors
def get_heatmap_data():
    """
    Get heatmap data for pickup and dropoff locations.
    ---
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Filter by start date
      - name: end_date
        in: query
        type: string
        format: date
        description: Filter by end date
    responses:
      200:
        description: Heatmap data points
    """
    cache_key = _cache_key("heatmap")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    limit = min(int(request.args.get('limit', 100)), 100)
    params['limit'] = limit
    
    query = f"""
        SELECT 
            ROUND(pickup_latitude, 4) as lat,
            ROUND(pickup_longitude, 4) as lng,
            COUNT(*) as count,
            AVG(fare_amount) as avg_fare,
            AVG(trip_duration_sec / 60.0) as avg_duration_minutes
        FROM trips t
        WHERE {where_clause}
        GROUP BY lat, lng
        HAVING count > 5
        ORDER BY count DESC
        LIMIT :limit
    """
    
    with get_db_connection() as conn:
        data = [dict(row) for row in conn.execute(query, params)]

    _cache_set(cache_key, data, ttl_seconds=30)
    return jsonify(data)

@api.route('/api/top_routes', methods=['GET'])
@handle_db_errors
def get_top_routes():
    """
    Get top routes by trip count.
    ---
    parameters:
      - name: limit
        in: query
        type: integer
        default: 100
        description: Number of routes to return
    responses:
      200:
        description: Top routes
    """
    cache_key = _cache_key("top_routes")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    
    limit = min(int(request.args.get('limit', 100)), 100)
    params['limit'] = limit
    
    query = f"""
        SELECT 
            ROUND(pickup_latitude, 4) as pickup_lat,
            ROUND(pickup_longitude, 4) as pickup_lng,
            ROUND(dropoff_latitude, 4) as dropoff_lat,
            ROUND(dropoff_longitude, 4) as dropoff_lng,
            COUNT(*) as trip_count,
            AVG(trip_distance_km) as avg_distance_km,
            AVG(fare_amount) as avg_fare,
            AVG(trip_duration_sec / 60.0) as avg_duration_minutes
        FROM trips t
        WHERE {where_clause}
        GROUP BY pickup_lat, pickup_lng, dropoff_lat, dropoff_lng
        ORDER BY trip_count DESC
        LIMIT :limit
    """
    
    with get_db_connection() as conn:
        routes = [dict(row) for row in conn.execute(query, params)]

    _cache_set(cache_key, routes, ttl_seconds=30)
    return jsonify(routes)

@api.route('/api/temporal_analysis', methods=['GET'])
@handle_db_errors
def get_temporal_analysis():
    """
    Get temporal analysis data (hourly, daily, monthly patterns).
    ---
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Filter by start date
      - name: end_date
        in: query
        type: string
        format: date
        description: Filter by end date
    responses:
      200:
        description: Temporal analysis data
    """
    cache_key = _cache_key("temporal_analysis")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    
    hourly_query = f"""
        SELECT 
            pickup_hour as hour,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            AVG(tip_amount) as avg_tip,
            AVG(avg_speed_kmh) as avg_speed_kmh
        FROM trips t
        WHERE {where_clause}
        GROUP BY pickup_hour
        ORDER BY pickup_hour
    """
    
    daily_query = f"""
        SELECT 
            pickup_weekday as day_of_week,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            AVG(trip_duration_sec / 60.0) as avg_duration_minutes
        FROM trips t
        WHERE {where_clause}
        GROUP BY pickup_weekday
        ORDER BY pickup_weekday
    """
    
    monthly_query = f"""
        SELECT 
            strftime('%Y-%m', pickup_datetime) as month,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            AVG(trip_distance_km) as avg_distance_km
        FROM trips t
        WHERE {where_clause}
        GROUP BY month
        ORDER BY month
    """
    
    with get_db_connection() as conn:
        hourly_data = [dict(row) for row in conn.execute(hourly_query, params)]
        daily_data = [dict(row) for row in conn.execute(daily_query, params)]
        monthly_data = [dict(row) for row in conn.execute(monthly_query, params)]
    
    payload = {
        'hourly': hourly_data,
        'daily': daily_data,
        'monthly': monthly_data
    }
    _cache_set(cache_key, payload, ttl_seconds=30)
    return jsonify(payload)

@api.route('/api/zones', methods=['GET'])
@handle_db_errors
def get_zones():
    """
    Get list of taxi zones.
    ---
    parameters:
      - name: borough
        in: query
        type: string
        description: Filter zones by borough
    responses:
      200:
        description: List of zones
    """
    cache_key = _cache_key("zones")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    borough = request.args.get('borough')
    with get_db_connection() as conn:
        if borough:
            zones = conn.execute(
                "SELECT location_id, borough, zone, service_zone FROM zones WHERE borough = ? ORDER BY zone",
                (borough,)
            ).fetchall()
        else:
            zones = conn.execute(
                "SELECT location_id, borough, zone, service_zone FROM zones ORDER BY borough, zone"
            ).fetchall()
    
    payload = [dict(row) for row in zones]
    _cache_set(cache_key, payload, ttl_seconds=300)
    return jsonify(payload)

@api.route('/api/zones/boroughs', methods=['GET'])
@handle_db_errors
def get_boroughs():
    """
    Get list of boroughs.
    ---
    responses:
      200:
        description: List of boroughs
    """
    cache_key = _cache_key("boroughs")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT borough FROM zones WHERE borough IS NOT NULL ORDER BY borough"
        ).fetchall()
    payload = [row["borough"] for row in rows]
    _cache_set(cache_key, payload, ttl_seconds=300)
    return jsonify(payload)

@api.route('/api/zones/geojson', methods=['GET'])
@handle_db_errors
def get_zones_geojson():
    """
    Get GeoJSON boundaries for taxi zones.
    ---
    parameters:
      - name: borough
        in: query
        type: string
        description: Filter by borough
      - name: zone
        in: query
        type: string
        description: Filter by zone name
    responses:
      200:
        description: GeoJSON FeatureCollection
    """
    cache_key = _cache_key("zones_geojson")
    cached_payload = _cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    borough = request.args.get('borough')
    zone = request.args.get('zone')
    params = {}
    conditions = []
    
    if borough:
        conditions.append("borough = :borough")
        params["borough"] = borough
    if zone:
        conditions.append("zone = :zone")
        params["zone"] = zone
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with get_db_connection() as conn:
        rows = conn.execute(
            f"SELECT location_id, borough, zone, service_zone, geometry FROM zones_geo WHERE {where_clause}",
            params
        ).fetchall()
    
    features = []
    for row in rows:
        geom = json.loads(row["geometry"]) if row["geometry"] else None
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "location_id": row["location_id"],
                "borough": row["borough"],
                "zone": row["zone"],
                "service_zone": row["service_zone"]
            }
        })
    
    payload = {"type": "FeatureCollection", "features": features}
    _cache_set(cache_key, payload, ttl_seconds=300)
    return jsonify(payload)
