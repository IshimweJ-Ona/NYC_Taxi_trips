#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
from datetime import datetime

NYC_LAT_MIN = 40.4774
NYC_LAT_MAX = 40.9176
NYC_LON_MIN = -74.2591
NYC_LON_MAX = -73.7004

MAX_SPEED_KMPH = 120.0
MAX_FARE = 500.0

def parse_float(v):
    try:
        return float(v) if v not in (None, "", "\\N") else None
    except Exception:
        return None

def parse_int(v):
    try:
        return int(v) if v not in (None, "", "\\N") else None
    except Exception:
        return None

def parse_dt(s):
    if not s:
        return None
    s = s.replace("T", " ").replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def in_bbox(lat, lon):
    if lat is None or lon is None:
        return False
    return NYC_LAT_MIN <= lat <= NYC_LAT_MAX and NYC_LON_MIN <= lon <= NYC_LON_MAX

def haversine_km(lat1, lon1, lat2, lon2):
    try:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return None

def get_field(row, names):
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="raw CSV path")
    p.add_argument("--output", required=True, help="cleaned CSV path")
    p.add_argument("--log", required=True, help="exclusions log (CSV)")
    p.add_argument("--stats", required=False, help="summary JSON path")
    p.add_argument("--distance-unit", choices=["miles", "km"], default="miles")
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.log) or ".", exist_ok=True)

    out_fields = [
        "pickup_datetime",
        "dropoff_datetime",
        "pickup_lat",
        "pickup_lon",
        "dropoff_lat",
        "dropoff_lon",
        "trip_distance_km",
        "trip_duration_sec",
        "fare_amount",
        "tip_amount",
        "passenger_count",
        "payment_type",
        "avg_speed_kmh",
        "fare_per_km",
        "pickup_hour",
        "weekday",
        "is_weekend",
        "haversine_km",
    ]

    total = cleaned = 0
    excluded = {}

    with open(args.input, newline="", encoding="utf-8") as fin, \
         open(args.output, "w", newline="", encoding="utf-8") as fout, \
         open(args.log, "w", newline="", encoding="utf-8") as flog:

        reader = csv.DictReader(fin)
        w = csv.DictWriter(fout, fieldnames=out_fields)
        w.writeheader()
        logw = csv.DictWriter(flog, fieldnames=["line", "reason", "pickup_ts", "dropoff_ts", "pickup_lat", "pickup_lon", "dropoff_lat", "dropoff_lon", "distance", "fare"])
        logw.writeheader()

        for i, row in enumerate(reader, start=1):
            total += 1

            p_ts = get_field(row, ["tpep_pickup_datetime", "pickup_datetime"]) or None
            d_ts = get_field(row, ["tpep_dropoff_datetime", "dropoff_datetime"]) or None
            p_dt = parse_dt(p_ts)
            d_dt = parse_dt(d_ts)
            if not p_dt or not d_dt or d_dt <= p_dt:
                r = "bad_timestamps"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "pickup_ts": p_ts, "dropoff_ts": d_ts})
                continue

            plat = parse_float(get_field(row, ["pickup_latitude", "pickup_lat"]))
            plon = parse_float(get_field(row, ["pickup_longitude", "pickup_lon", "pickup_lng"]))
            dlat = parse_float(get_field(row, ["dropoff_latitude", "dropoff_lat"]))
            dlon = parse_float(get_field(row, ["dropoff_longitude", "dropoff_lon", "dropoff_lng"]))
            if not in_bbox(plat, plon) or not in_bbox(dlat, dlon):
                r = "bad_coordinates"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "pickup_lat": plat, "pickup_lon": plon, "dropoff_lat": dlat, "dropoff_lon": dlon})
                continue

            # Some datasets don't provide trip_distance; compute from haversine as fallback
            reported_dist = parse_float(get_field(row, ["trip_distance", "distance", "trip_distance_km"]))
            hv_km_pre = haversine_km(plat, plon, dlat, dlon)
            if reported_dist is not None:
                dist_km = reported_dist * 1.60934 if args.distance_unit == "miles" else reported_dist
            else:
                dist_km = hv_km_pre  # fallback to haversine distance when trip_distance missing
            if dist_km is None or dist_km < 0:
                r = "bad_distance"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "distance": dist_km})
                continue
            if dist_km == 0:
                r = "zero_distance"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "distance": dist_km})
                continue

            # Fares may be missing in this dataset; allow NULL fares and tips
            fare = parse_float(get_field(row, ["fare_amount", "fare", "total_amount"]))
            tip = parse_float(get_field(row, ["tip_amount", "tip"]))
            if fare is not None and (fare < 0 or fare > MAX_FARE):
                r = "bad_fare"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "fare": fare})
                continue
            if tip is not None and tip < 0:
                r = "bad_tip"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "fare": fare})
                continue

            duration_sec = int((d_dt - p_dt).total_seconds())
            if duration_sec <= 0:
                r = "nonpositive_duration"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r})
                continue

            hours = duration_sec / 3600.0
            avg_speed_kmh = dist_km / hours if hours > 0 else 0.0
            if avg_speed_kmh > MAX_SPEED_KMPH:
                r = "implausible_speed"
                excluded[r] = excluded.get(r, 0) + 1
                logw.writerow({"line": i, "reason": r, "distance": dist_km})
                continue

            fare_per_km = (fare / dist_km) if (fare is not None and dist_km > 0) else None
            pickup_hour = p_dt.hour
            weekday = p_dt.weekday()
            is_weekend = 1 if weekday >= 5 else 0
            hv_km = hv_km_pre

            out = {
                "pickup_datetime": p_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "dropoff_datetime": d_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "pickup_lat": round(plat, 6) if plat is not None else None,
                "pickup_lon": round(plon, 6) if plon is not None else None,
                "dropoff_lat": round(dlat, 6) if dlat is not None else None,
                "dropoff_lon": round(dlon, 6) if dlon is not None else None,
                "trip_distance_km": round(dist_km, 6),
                "trip_duration_sec": duration_sec,
                "fare_amount": round(fare, 2) if fare is not None else None,
                "tip_amount": round(tip, 2) if tip is not None else 0.0,
                "passenger_count": parse_int(get_field(row, ["passenger_count", "passengers"])) or 1,
                "payment_type": get_field(row, ["payment_type", "payment"]),
                "avg_speed_kmh": round(avg_speed_kmh, 3),
                "fare_per_km": round(fare_per_km, 3) if fare_per_km is not None else None,
                "pickup_hour": pickup_hour,
                "weekday": weekday,
                "is_weekend": is_weekend,
                "haversine_km": round(hv_km, 3) if hv_km is not None else None,
            }

            w.writerow(out)
            cleaned += 1

    summary = {
        "total_rows": total,
        "cleaned_rows": cleaned,
        "excluded_rows": total - cleaned,
        "excluded_counts": excluded,
    }
    if args.stats:
        with open(args.stats, "w", encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
