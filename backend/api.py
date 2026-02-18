#!/usr/bin/env python3
import os
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from functools import wraps
from algorithms import manual_bubble_sort_trips_by_fare, manual_filter_trips_by_distance

api = Blueprint('api', __name__)

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

def build_where_clause(filters):
    conditions = []
    params = {}
    
    if 'start_date' in filters:
        conditions.append("DATE(pickup_datetime) >= :start_date")
        params['start_date'] = filters['start_date']
    if 'end_date' in filters:
        conditions.append("DATE(pickup_datetime) <= :end_date")
        params['end_date'] = filters['end_date']
    
    if 'pickup_lat' in filters and 'pickup_lon' in filters:
        conditions.append("""
            pickup_latitude BETWEEN :min_pickup_lat AND :max_pickup_lat
            AND pickup_longitude BETWEEN :min_pickup_lon AND :max_pickup_lon
        """)
        params.update({
            'min_pickup_lat': float(filters['pickup_lat']) - 0.01,
            'max_pickup_lat': float(filters['pickup_lat']) + 0.01,
            'min_pickup_lon': float(filters['pickup_lon']) - 0.01,
            'max_pickup_lon': float(filters['pickup_lon']) + 0.01,
        })
    
    if 'min_distance' in filters:
        conditions.append("trip_distance_km >= :min_distance")
        params['min_distance'] = float(filters['min_distance'])
    if 'max_distance' in filters:
        conditions.append("trip_distance_km <= :max_distance")
        params['max_distance'] = float(filters['max_distance'])
    
    if 'min_fare' in filters:
        conditions.append("fare_amount >= :min_fare")
        params['min_fare'] = float(filters['min_fare'])
    if 'max_fare' in filters:
        conditions.append("fare_amount <= :max_fare")
        params['max_fare'] = float(filters['max_fare'])
    
    if 'passenger_count' in filters:
        conditions.append("passenger_count = :passenger_count")
        params['passenger_count'] = int(filters['passenger_count'])
    
    if 'payment_type' in filters:
        conditions.append("payment_type_id = :payment_type")
        params['payment_type'] = int(filters['payment_type'])
    
    if 'is_peak_hour' in filters:
        conditions.append("is_peak_hour = :is_peak_hour")
        params['is_peak_hour'] = 1 if filters['is_peak_hour'].lower() == 'true' else 0
    
    if 'is_weekend' in filters:
        conditions.append("is_weekend = :is_weekend")
        params['is_weekend'] = 1 if filters['is_weekend'].lower() == 'true' else 0
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params

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
        default: 50
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
    per_page = min(int(request.args.get('per_page', 50)), 100)
    offset = (page - 1) * per_page
    
    filters = {k: v for k, v in request.args.items() 
              if k not in ['page', 'per_page', 'sort', 'order']}
    
    where_clause, params = build_where_clause(filters)
    params.update({'limit': per_page, 'offset': offset})
    
    sort = request.args.get('sort', 'pickup_datetime')
    order = request.args.get('order', 'desc')
    order_by = f"{sort} {order.upper()}"
    
    use_custom_sort = request.args.get('custom_sort', 'false').lower() == 'true'
    
    with get_db_connection() as conn:
        count_query = f"""
            SELECT COUNT(*) as total 
            FROM trips 
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
            
            print("Applying Manual Bubble Sort...")
            sorted_trips = manual_bubble_sort_trips_by_fare(all_trips, ascending=False)
            
            start = offset
            end = offset + per_page
            trips = sorted_trips[start:end]
            
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
    
    response = {
        'data': trips,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        },
        'algorithm_used': 'Manual Bubble Sort' if use_custom_sort else 'SQL Order By'
    }
    
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
    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    
    with get_db_connection() as conn:
        query = f"""
            SELECT 
                COUNT(*) as total_trips,
                AVG(trip_distance_km) as avg_distance_km,
                AVG(fare_amount) as avg_fare,
                AVG(tip_amount) as avg_tip,
                AVG(tip_amount / NULLIF(fare_amount, 0)) * 100 as avg_tip_percentage,
                AVG(avg_speed_kmh) as avg_speed_kmh,
                AVG(fare_per_km) as avg_fare_per_km,
                AVG(trip_efficiency) as avg_efficiency,
                SUM(CASE WHEN is_peak_hour = 1 THEN 1 ELSE 0 END) as peak_hour_trips,
                SUM(CASE WHEN is_weekend = 1 THEN 1 ELSE 0 END) as weekend_trips
            FROM trips
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
                AVG(fare_amount) as avg_fare,
                AVG(tip_amount) as avg_tip
            FROM trips
            WHERE {where_clause}
            GROUP BY pickup_hour
            ORDER BY pickup_hour
        """
        hourly_data = [dict(row) for row in conn.execute(hourly_query, params)]
    
    summary = dict(result)
    summary['payment_distribution'] = payment_dist
    summary['hourly_distribution'] = hourly_data
    
    return jsonify(summary)

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
    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    
    query = f"""
        SELECT 
            ROUND(pickup_latitude, 4) as lat,
            ROUND(pickup_longitude, 4) as lng,
            COUNT(*) as count,
            AVG(fare_amount) as avg_fare,
            AVG(trip_duration_sec / 60.0) as avg_duration_minutes
        FROM trips
        WHERE {where_clause}
        GROUP BY lat, lng
        HAVING count > 5
    """
    
    with get_db_connection() as conn:
        data = [dict(row) for row in conn.execute(query, params)]
    
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
        default: 10
        description: Number of routes to return
    responses:
      200:
        description: Top routes
    """
    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    
    limit = min(int(request.args.get('limit', 10)), 50)
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
        FROM trips
        WHERE {where_clause}
        GROUP BY pickup_lat, pickup_lng, dropoff_lat, dropoff_lng
        ORDER BY trip_count DESC
        LIMIT :limit
    """
    
    with get_db_connection() as conn:
        routes = [dict(row) for row in conn.execute(query, params)]
    
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
    filters = dict(request.args)
    where_clause, params = build_where_clause(filters)
    
    hourly_query = f"""
        SELECT 
            pickup_hour as hour,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            AVG(tip_amount) as avg_tip,
            AVG(avg_speed_kmh) as avg_speed_kmh
        FROM trips
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
        FROM trips
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
        FROM trips
        WHERE {where_clause}
        GROUP BY month
        ORDER BY month
    """
    
    with get_db_connection() as conn:
        hourly_data = [dict(row) for row in conn.execute(hourly_query, params)]
        daily_data = [dict(row) for row in conn.execute(daily_query, params)]
        monthly_data = [dict(row) for row in conn.execute(monthly_query, params)]
    
    return jsonify({
        'hourly': hourly_data,
        'daily': daily_data,
        'monthly': monthly_data
    })
