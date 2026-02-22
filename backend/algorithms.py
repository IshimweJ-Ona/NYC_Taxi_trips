NUMERIC_SORT_FIELDS = {
    "fare_amount",
    "trip_distance_km",
    "tip_amount",
    "avg_speed_kmh",
    "trip_duration_sec",
    "passenger_count",
}


def _to_numeric(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _compare_values(left, right, ascending=True):
    if ascending:
        return left <= right
    return left >= right


def _build_sort_value(trip, sort_field):
    raw = trip.get(sort_field)
    if sort_field in NUMERIC_SORT_FIELDS:
        return _to_numeric(raw)
    if raw is None:
        return ""
    return str(raw)


def manual_merge_sort_trips(trips, sort_field="fare_amount", ascending=True):
    """
    Iterative, stable merge sort to avoid Python built-in sorting.
    Returns a new list sorted by sort_field.
    """
    size = len(trips)
    if size <= 1:
        return list(trips)

    source = list(trips)
    target = [None] * size
    width = 1

    while width < size:
        left = 0
        while left < size:
            mid = left + width
            right = left + (width * 2)

            if mid > size:
                mid = size
            if right > size:
                right = size

            i = left
            j = mid
            k = left

            while i < mid and j < right:
                left_value = _build_sort_value(source[i], sort_field)
                right_value = _build_sort_value(source[j], sort_field)

                if _compare_values(left_value, right_value, ascending):
                    target[k] = source[i]
                    i += 1
                else:
                    target[k] = source[j]
                    j += 1
                k += 1

            while i < mid:
                target[k] = source[i]
                i += 1
                k += 1

            while j < right:
                target[k] = source[j]
                j += 1
                k += 1

            left += width * 2

        source, target = target, source
        width *= 2

    return source


def manual_bubble_sort_trips_by_fare(trips, ascending=True):
    # Kept for compatibility; now delegates to faster O(n log n) sort.
    return manual_merge_sort_trips(
        trips,
        sort_field="fare_amount",
        ascending=ascending,
    )


def manual_filter_trips_by_distance(trips, min_dist, max_dist):
    filtered_trips = []
    index = 0
    while index < len(trips):
        trip = trips[index]
        dist = trip.get("trip_distance_km", 0)

        if dist >= min_dist and dist <= max_dist:
            filtered_trips.append(trip)

        index += 1

    return filtered_trips
