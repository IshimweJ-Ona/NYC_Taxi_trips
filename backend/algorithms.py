def manual_bubble_sort_trips_by_fare(trips, ascending=True):
    n = len(trips)
    for i in range(n):
        for j in range(0, n-i-1):
            
            val1 = trips[j].get('fare_amount', 0)
            val2 = trips[j+1].get('fare_amount', 0)
            
            should_swap = False
            if ascending:
                if val1 > val2:
                    should_swap = True
            else:
                if val1 < val2:
                    should_swap = True
            
            if should_swap:
                trips[j], trips[j+1] = trips[j+1], trips[j]
                
    return trips

def manual_filter_trips_by_distance(trips, min_dist, max_dist):
    filtered_trips = []
    index = 0
    while index < len(trips):
        trip = trips[index]
        dist = trip.get('trip_distance_km', 0)
        
        if dist >= min_dist and dist <= max_dist:
            filtered_trips.append(trip)
            
        index += 1
        
    return filtered_trips
