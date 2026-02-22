// ==========================================
// NYC URBAN MOBILITY EXPLORER
// Frontend Application - Integrated with Backend API
// ==========================================

// API Configuration
const API_BASE = 'http://localhost:5000';
const CLEANED_DATA_BASE = `${API_BASE}/cleaned_data`;
const ZONES_CSV_PATH = `${CLEANED_DATA_BASE}/zones_cleaned.csv`;
const ZONES_GEOJSON_PATH = `${CLEANED_DATA_BASE}/zones_geo_cleaned.geojson`;

// Global State Management
const AppState = {
    allTrips: [],
    currentPage: 1,
    tripsPerPage: 100,
    totalTrips: 0,
    totalPages: 1,
    sortColumn: 'pickup_datetime',
    sortDirection: 'desc',
    filters: {
        start_date: null,
        end_date: null,
        min_distance: 0,
        max_distance: 100,
        min_fare: 0,
        max_fare: 200,
        is_peak_hour: null,
        is_weekend: null,
        passenger_count: null,
        payment_type: null,
        pickup_borough: null,
        pickup_zone: null,
        dropoff_borough: null,
        dropoff_zone: null
    },
    charts: {},
    map: null,
    mapRenderer: null,
    mapLayerGroup: null,
    mapMarkers: [],
    mapMode: 'pickups',
    mapLimit: 50,
    useCustomSort: false,
    summary: null,
    zones: [],
    boroughs: [],
    zonesGeoJson: null,
    zoneLayer: null,
    zoneLayerVisible: false,
    zoneLayerKey: null,
    dashboardCache: {},
    dashboardController: null,
    filterDebounceTimer: null
};

// Prefer the canonical id field from the API, but fall back for legacy data.
function getTripId(trip) {
    return trip.id ?? trip.trip_id;
}

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('NYC Urban Mobility Explorer - Initializing...');
    
    setTimeout(() => {
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {
            loadingScreen.style.display = 'none';
        }
    }, 1500);
    
    await initializeApp();
    setupEventListeners();
    initializeCharts();
    initializeMap();
});

// ==========================================
// DATA FETCHING
// ==========================================
async function initializeApp() {
    try {
        console.log('Fetching trip data from API...');
        
        await fetchZonesMetadata();
        await fetchDashboard(1, false, true);
        
        updateDashboard();
        fetchDashboard(1, true, false).then(() => {
            updateHeroStats();
            updateCharts();
        }).catch((error) => {
            console.error('Error refreshing summary payload:', error);
        });
        
        console.log(`✓ Loaded ${AppState.totalTrips.toLocaleString()} total trips`);
        
    } catch (error) {
        console.error('Error initializing app:', error);
        showErrorMessage('Failed to load data. Please check backend connection.');
    }
}

function applyDashboardPayload(payload) {
    const summary = payload && payload.summary ? payload.summary : null;
    const tripsPart = payload && payload.trips ? payload.trips : null;

    if (summary) {
        AppState.summary = summary;
    }
    if (tripsPart) {
        const pagination = tripsPart.pagination || {};
        AppState.allTrips = tripsPart.data || [];
        AppState.totalTrips = pagination.total || 0;
        AppState.totalPages = pagination.total_pages || 1;
        AppState.currentPage = pagination.page || 1;
    }
}

function buildDashboardParams(page = 1, includeSummary = true, includeTrips = true) {
    const params = new URLSearchParams({
        page: page,
        per_page: AppState.tripsPerPage,
        sort: AppState.sortColumn,
        order: AppState.sortDirection,
        include_summary: includeSummary ? 'true' : 'false',
        include_trips: includeTrips ? 'true' : 'false'
    });
    appendTripFilters(params);
    if (AppState.useCustomSort) {
        params.append('custom_sort', 'true');
    }
    return params;
}

async function fetchDashboard(page = 1, includeSummary = true, includeTrips = true) {
    const params = buildDashboardParams(page, includeSummary, includeTrips);
    const cacheKey = params.toString();
    const now = Date.now();
    const cacheEntry = AppState.dashboardCache[cacheKey];
    if (cacheEntry && (now - cacheEntry.ts) < 15000) {
        applyDashboardPayload(cacheEntry.payload);
        return cacheEntry.payload;
    }

    if (AppState.dashboardController) {
        AppState.dashboardController.abort();
    }
    const controller = new AbortController();
    AppState.dashboardController = controller;

    try {
        const response = await fetch(`${API_BASE}/api/dashboard?${cacheKey}`, {
            signal: controller.signal
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const payload = await response.json();
        AppState.dashboardCache[cacheKey] = {
            ts: now,
            payload: payload
        };
        const cacheKeys = Object.keys(AppState.dashboardCache);
        if (cacheKeys.length > 100) {
            let oldestKey = cacheKeys[0];
            let oldestTs = AppState.dashboardCache[oldestKey].ts;
            let idx = 1;
            while (idx < cacheKeys.length) {
                const key = cacheKeys[idx];
                const ts = AppState.dashboardCache[key].ts;
                if (ts < oldestTs) {
                    oldestTs = ts;
                    oldestKey = key;
                }
                idx += 1;
            }
            delete AppState.dashboardCache[oldestKey];
        }
        applyDashboardPayload(payload);
        return payload;
    } catch (error) {
        if (error && error.name === 'AbortError') {
            return null;
        }
        console.error('Error fetching dashboard payload:', error);
        throw error;
    } finally {
        if (AppState.dashboardController === controller) {
            AppState.dashboardController = null;
        }
    }
}

async function fetchTrips(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: AppState.tripsPerPage,
            sort: AppState.sortColumn,
            order: AppState.sortDirection
        });
        
        appendTripFilters(params);
        
        // Add custom sort if enabled
        if (AppState.useCustomSort) {
            params.append('custom_sort', 'true');
        }
        
        const response = await fetch(`${API_BASE}/api/trips?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        AppState.allTrips = data.data || [];
        AppState.totalTrips = data.pagination.total;
        AppState.totalPages = data.pagination.total_pages;
        AppState.currentPage = data.pagination.page;
        
        console.log(`✓ Fetched ${AppState.allTrips.length} trips (page ${page})`);
        if (data.algorithm_used) {
            console.log(`  Algorithm: ${data.algorithm_used}`);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching trips:', error);
        throw error;
    }
}

async function fetchSummary() {
    try {
        const params = new URLSearchParams();
        
        // Add date filters if set
        if (AppState.filters.start_date) {
            params.append('start_date', AppState.filters.start_date);
        }
        if (AppState.filters.end_date) {
            params.append('end_date', AppState.filters.end_date);
        }
        
        const response = await fetch(`${API_BASE}/api/summary?${params.toString()}`);
        const data = await response.json();
        
        AppState.summary = data;
        console.log('✓ Summary data loaded');
        
        return data;
    } catch (error) {
        console.error('Error fetching summary:', error);
        return null;
    }
}

async function fetchZonesMetadata() {
    try {
        const zonesCsvResponse = await fetch(ZONES_CSV_PATH);
        if (!zonesCsvResponse.ok) {
            throw new Error(`Unable to load ${ZONES_CSV_PATH}`);
        }
        const zonesCsvText = await zonesCsvResponse.text();
        AppState.zones = parseZonesCsv(zonesCsvText);
        AppState.zones = ManualAlgorithms.mergeSortObjectsByField(AppState.zones, 'zone', true);

        const boroughValues = ManualAlgorithms.uniqueFieldValues(AppState.zones, 'borough');
        const boroughRecords = [];
        let index = 0;
        while (index < boroughValues.length) {
            boroughRecords.push({ borough: boroughValues[index] });
            index += 1;
        }
        const sortedBoroughRecords = ManualAlgorithms.mergeSortObjectsByField(boroughRecords, 'borough', true);
        AppState.boroughs = [];
        index = 0;
        while (index < sortedBoroughRecords.length) {
            AppState.boroughs.push(sortedBoroughRecords[index].borough);
            index += 1;
        }

        const zonesGeoResponse = await fetch(ZONES_GEOJSON_PATH);
        if (!zonesGeoResponse.ok) {
            throw new Error(`Unable to load ${ZONES_GEOJSON_PATH}`);
        }
        AppState.zonesGeoJson = await zonesGeoResponse.json();

        populateBoroughSelects();
        populateZoneSelects();

        console.log('Zone metadata loaded from cleaned_data');
    } catch (error) {
        console.error('Error fetching zone metadata:', error);
    }
}

function parseZonesCsv(csvText) {
    const rows = [];
    const lines = csvText.replace(/\r/g, '').split('\n');
    if (lines.length <= 1) {
        return rows;
    }

    let index = 1;
    while (index < lines.length) {
        const line = lines[index];
        if (!line || !line.trim()) {
            index += 1;
            continue;
        }

        const columns = line.split(',');
        if (columns.length >= 4) {
            const locationId = Number(columns[0].trim());
            if (!Number.isNaN(locationId)) {
                rows.push({
                    location_id: locationId,
                    borough: columns[1].trim(),
                    zone: columns[2].trim(),
                    service_zone: columns[3].trim()
                });
            }
        }
        index += 1;
    }

    return rows;
}

function appendTripFilters(params) {
    const directFilterKeys = [
        'start_date',
        'end_date',
        'min_distance',
        'max_distance',
        'min_fare',
        'max_fare',
        'is_peak_hour',
        'is_weekend',
        'passenger_count',
        'payment_type'
    ];

    let index = 0;
    while (index < directFilterKeys.length) {
        const key = directFilterKeys[index];
        const value = AppState.filters[key];
        if (value !== null && value !== '' && value !== 'all') {
            params.append(key, value);
        }
        index += 1;
    }

    const pickupZone = AppState.filters.pickup_zone;
    const dropoffZone = AppState.filters.dropoff_zone;
    const pickupBorough = AppState.filters.pickup_borough;
    const dropoffBorough = AppState.filters.dropoff_borough;

    if (pickupZone) {
        const zone = findZoneByName(pickupZone, pickupBorough);
        if (zone) {
            params.append('pu_location_id', zone.location_id);
        }
    } else if (pickupBorough) {
        const pickupIds = getLocationIdsByBorough(pickupBorough);
        if (pickupIds.length > 0) {
            params.append('pu_location_ids', pickupIds.join(','));
        }
    }

    if (dropoffZone) {
        const zone = findZoneByName(dropoffZone, dropoffBorough);
        if (zone) {
            params.append('do_location_id', zone.location_id);
        }
    } else if (dropoffBorough) {
        const dropoffIds = getLocationIdsByBorough(dropoffBorough);
        if (dropoffIds.length > 0) {
            params.append('do_location_ids', dropoffIds.join(','));
        }
    }
}

function findZoneByName(zoneName, boroughName = null) {
    let index = 0;
    while (index < AppState.zones.length) {
        const zone = AppState.zones[index];
        if (zone.zone === zoneName) {
            if (!boroughName || boroughName === 'all' || zone.borough === boroughName) {
                return zone;
            }
        }
        index += 1;
    }
    return null;
}

function getLocationIdsByBorough(boroughName) {
    const ids = [];
    let index = 0;
    while (index < AppState.zones.length) {
        const zone = AppState.zones[index];
        if (zone.borough === boroughName) {
            ids.push(zone.location_id);
        }
        index += 1;
    }
    return ids;
}

// ==========================================
// EVENT LISTENERS
// ==========================================
function setupEventListeners() {
    // Filter changes
    document.getElementById('min-distance')?.addEventListener('change', handleFilterChange);
    document.getElementById('max-distance')?.addEventListener('change', handleFilterChange);
    document.getElementById('min-fare')?.addEventListener('change', handleFilterChange);
    document.getElementById('max-fare')?.addEventListener('change', handleFilterChange);
    document.getElementById('peak-filter')?.addEventListener('change', handleFilterChange);
    document.getElementById('weekend-filter')?.addEventListener('change', handleFilterChange);
    document.getElementById('pickup-borough-filter')?.addEventListener('change', () => {
        updateZoneOptions('pickup-zone-filter', document.getElementById('pickup-borough-filter')?.value);
        handleFilterChange();
    });
    document.getElementById('pickup-zone-filter')?.addEventListener('change', handleFilterChange);
    document.getElementById('dropoff-borough-filter')?.addEventListener('change', () => {
        updateZoneOptions('dropoff-zone-filter', document.getElementById('dropoff-borough-filter')?.value);
        handleFilterChange();
    });
    document.getElementById('dropoff-zone-filter')?.addEventListener('change', handleFilterChange);
    
    // Reset filters
    document.getElementById('reset-filters')?.addEventListener('click', resetFilters);
    
    // Export CSV
    document.getElementById('export-csv')?.addEventListener('click', exportToCSV);
    
    // Pagination
    document.getElementById('prev-page')?.addEventListener('click', () => changePage(-1));
    document.getElementById('next-page')?.addEventListener('click', () => changePage(1));
    
    // Custom sort toggle
    document.getElementById('custom-sort-toggle')?.addEventListener('change', (e) => {
        AppState.useCustomSort = e.target.checked;
        handleFilterChange();
    });
    
    // Modal close
    const modal = document.getElementById('trip-modal');
    document.querySelector('.modal-close')?.addEventListener('click', () => {
        modal?.classList.remove('active');
    });
    document.querySelector('.modal-overlay')?.addEventListener('click', () => {
        modal?.classList.remove('active');
    });
    
    // Map controls
    document.getElementById('show-pickups')?.addEventListener('click', () => setMapMode('pickups'));
    document.getElementById('show-dropoffs')?.addEventListener('click', () => setMapMode('dropoffs'));
    document.getElementById('show-heatmap')?.addEventListener('click', () => setMapMode('heatmap'));
    document.getElementById('map-limit')?.addEventListener('change', (e) => {
        AppState.mapLimit = parseInt(e.target.value);
        updateMap();
    });
    document.getElementById('zone-layer-toggle')?.addEventListener('change', (e) => {
        AppState.zoneLayerVisible = e.target.checked;
        updateZoneLayer();
    });
}

// ==========================================
// FILTER HANDLING
// ==========================================
async function handleFilterChange() {
    // Update filter state from inputs
    AppState.filters.min_distance = parseFloat(document.getElementById('min-distance')?.value || 0);
    AppState.filters.max_distance = parseFloat(document.getElementById('max-distance')?.value || 100);
    AppState.filters.min_fare = parseFloat(document.getElementById('min-fare')?.value || 0);
    AppState.filters.max_fare = parseFloat(document.getElementById('max-fare')?.value || 200);
    
    const peakValue = document.getElementById('peak-filter')?.value;
    AppState.filters.is_peak_hour = peakValue === 'all' ? null : (peakValue === 'peak' ? 'true' : 'false');
    
    const weekendValue = document.getElementById('weekend-filter')?.value;
    AppState.filters.is_weekend = weekendValue === 'all' ? null : (weekendValue === 'weekend' ? 'true' : 'false');
    
    const pickupBorough = document.getElementById('pickup-borough-filter')?.value;
    AppState.filters.pickup_borough = pickupBorough === 'all' ? null : pickupBorough;
    
    const pickupZone = document.getElementById('pickup-zone-filter')?.value;
    AppState.filters.pickup_zone = pickupZone === 'all' ? null : pickupZone;
    
    const dropoffBorough = document.getElementById('dropoff-borough-filter')?.value;
    AppState.filters.dropoff_borough = dropoffBorough === 'all' ? null : dropoffBorough;
    
    const dropoffZone = document.getElementById('dropoff-zone-filter')?.value;
    AppState.filters.dropoff_zone = dropoffZone === 'all' ? null : dropoffZone;
    
    // Reset to page 1
    AppState.currentPage = 1;
    
    if (AppState.filterDebounceTimer) {
        clearTimeout(AppState.filterDebounceTimer);
    }
    AppState.filterDebounceTimer = setTimeout(async () => {
        await fetchDashboard(1, false, true);
        updateDashboard();
        updateZoneLayer();
        fetchDashboard(1, true, false).then(() => {
            updateHeroStats();
            updateCharts();
        }).catch((error) => {
            console.error('Error refreshing summary payload:', error);
        });
    }, 180);
}

function resetFilters() {
    // Reset controls
    if (document.getElementById('min-distance')) document.getElementById('min-distance').value = 0;
    if (document.getElementById('max-distance')) document.getElementById('max-distance').value = 100;
    if (document.getElementById('min-fare')) document.getElementById('min-fare').value = 0;
    if (document.getElementById('max-fare')) document.getElementById('max-fare').value = 200;
    if (document.getElementById('peak-filter')) document.getElementById('peak-filter').value = 'all';
    if (document.getElementById('weekend-filter')) document.getElementById('weekend-filter').value = 'all';
    if (document.getElementById('pickup-borough-filter')) document.getElementById('pickup-borough-filter').value = 'all';
    if (document.getElementById('pickup-zone-filter')) document.getElementById('pickup-zone-filter').value = 'all';
    if (document.getElementById('dropoff-borough-filter')) document.getElementById('dropoff-borough-filter').value = 'all';
    if (document.getElementById('dropoff-zone-filter')) document.getElementById('dropoff-zone-filter').value = 'all';
    if (document.getElementById('custom-sort-toggle')) document.getElementById('custom-sort-toggle').checked = false;
    
    // Reset state
    AppState.filters = {
        start_date: null,
        end_date: null,
        min_distance: 0,
        max_distance: 100,
        min_fare: 0,
        max_fare: 200,
        is_peak_hour: null,
        is_weekend: null,
        passenger_count: null,
        payment_type: null,
        pickup_borough: null,
        pickup_zone: null,
        dropoff_borough: null,
        dropoff_zone: null
    };
    AppState.useCustomSort = false;
    AppState.currentPage = 1;
    
    // Reload data
    handleFilterChange();
}

// ==========================================
// DASHBOARD UPDATE
// ==========================================
function updateDashboard() {
    updateHeroStats();
    updateTable();
    updateCharts();
    updateMap();
}

function updateHeroStats() {
    if (!AppState.summary) return;
    
    const totalTrips = AppState.summary.total_trips || 0;
    const avgDistance = AppState.summary.avg_distance_km || 0;
    const avgFare = AppState.summary.avg_fare || 0;
    const avgSpeed = AppState.summary.avg_speed_kmh || 0;
    
    const totalTripsEl = document.getElementById('total-trips');
    const avgDistanceEl = document.getElementById('avg-distance');
    const avgDurationEl = document.getElementById('avg-duration');
    const totalRevenueEl = document.getElementById('total-revenue');
    
    if (totalTripsEl) totalTripsEl.textContent = totalTrips.toLocaleString();
    if (avgDistanceEl) avgDistanceEl.textContent = avgDistance.toFixed(2) + ' km';
    if (avgDurationEl) avgDurationEl.textContent = avgSpeed.toFixed(1) + ' km/h';
    if (totalRevenueEl) totalRevenueEl.textContent = '$' + avgFare.toFixed(2);
}

// ==========================================
// TABLE RENDERING
// ==========================================
function updateTable() {
    const tbody = document.getElementById('trips-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    AppState.allTrips.forEach(trip => {
        const row = createTableRow(trip);
        tbody.appendChild(row);
    });
    
    updatePagination();
    
    // Update count
    const showingCount = document.getElementById('showing-count');
    const totalCount = document.getElementById('total-count');
    if (showingCount) showingCount.textContent = AppState.allTrips.length;
    if (totalCount) totalCount.textContent = AppState.totalTrips.toLocaleString();
}

function createTableRow(trip) {
    const row = document.createElement('tr');
    const tripId = getTripId(trip);
    
    // Convert seconds to minutes
    const durationMinutes = Math.round(trip.trip_duration_sec / 60);
    
    row.innerHTML = `
        <td>${formatDateTime(trip.pickup_datetime)}</td>
        <td>${trip.pickup_latitude?.toFixed(4) || 'N/A'}, ${trip.pickup_longitude?.toFixed(4) || 'N/A'}</td>
        <td>${trip.dropoff_latitude?.toFixed(4) || 'N/A'}, ${trip.dropoff_longitude?.toFixed(4) || 'N/A'}</td>
        <td>${trip.trip_distance_km?.toFixed(2) || 0} km</td>
        <td>${formatDuration(durationMinutes)}</td>
        <td>$${trip.fare_amount?.toFixed(2) || 0}</td>
        <td>${trip.passenger_count || 0}</td>
        <td>
            <button onclick="showTripDetails(${tripId})">View</button>
        </td>
    `;
    
    return row;
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function formatDuration(minutes) {
    if (minutes < 60) {
        return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
}

// ==========================================
// PAGINATION
// ==========================================
function updatePagination() {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const pageNumbers = document.getElementById('page-numbers');
    
    if (prevBtn) prevBtn.disabled = AppState.currentPage === 1;
    if (nextBtn) nextBtn.disabled = AppState.currentPage === AppState.totalPages;
    
    if (!pageNumbers) return;
    
    pageNumbers.innerHTML = '';
    
    const maxPages = 5;
    let startPage = Math.max(1, AppState.currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(AppState.totalPages, startPage + maxPages - 1);
    
    if (endPage - startPage < maxPages - 1) {
        startPage = Math.max(1, endPage - maxPages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('div');
        pageBtn.className = 'page-number' + (i === AppState.currentPage ? ' active' : '');
        pageBtn.textContent = i;
        pageBtn.addEventListener('click', () => goToPage(i));
        pageNumbers.appendChild(pageBtn);
    }
}

async function changePage(delta) {
    const currentPage = Number(AppState.currentPage) || 1;
    const totalPages = Number(AppState.totalPages) || 1;
    const newPage = currentPage + delta;

    if (newPage >= 1 && newPage <= totalPages) {
        await goToPage(newPage);
    }
}

async function goToPage(page) {
    const nextPage = Number(page);
    if (!Number.isInteger(nextPage) || nextPage < 1) return;

    AppState.currentPage = nextPage;
    await fetchTrips(nextPage);
    updateDashboard();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// TRIP DETAILS MODAL
// ==========================================
function showTripDetails(tripId) {
    const trip = AppState.allTrips.find(t => getTripId(t) === tripId);
    if (!trip) return;
    
    const modal = document.getElementById('trip-modal');
    const modalBody = document.getElementById('modal-body');
    
    if (!modalBody) return;
    
    const durationMinutes = Math.round(trip.trip_duration_sec / 60);
    
    modalBody.innerHTML = `
        <div class="detail-row">
            <span class="detail-label">Trip ID:</span>
            <span class="detail-value">#${getTripId(trip)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Pickup Time:</span>
            <span class="detail-value">${new Date(trip.pickup_datetime).toLocaleString()}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Dropoff Time:</span>
            <span class="detail-value">${new Date(trip.dropoff_datetime).toLocaleString()}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Duration:</span>
            <span class="detail-value">${formatDuration(durationMinutes)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Pickup Hour:</span>
            <span class="detail-value">${trip.pickup_hour}:00 ${trip.is_peak_hour === 1 ? '(Peak Hour)' : '(Off-Peak)'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Day Type:</span>
            <span class="detail-value">${trip.is_weekend === 1 ? 'Weekend' : 'Weekday'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Pickup Location:</span>
            <span class="detail-value">Lat: ${trip.pickup_latitude?.toFixed(4)}, Lng: ${trip.pickup_longitude?.toFixed(4)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Dropoff Location:</span>
            <span class="detail-value">Lat: ${trip.dropoff_latitude?.toFixed(4)}, Lng: ${trip.dropoff_longitude?.toFixed(4)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Distance:</span>
            <span class="detail-value">${trip.trip_distance_km?.toFixed(2)} km</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Average Speed:</span>
            <span class="detail-value">${trip.avg_speed_kmh?.toFixed(1)} km/h</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Fare Amount:</span>
            <span class="detail-value">$${trip.fare_amount?.toFixed(2)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Tip Amount:</span>
            <span class="detail-value">$${trip.tip_amount?.toFixed(2)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Total Amount:</span>
            <span class="detail-value">$${trip.total_amount?.toFixed(2)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Fare per KM:</span>
            <span class="detail-value">$${trip.fare_per_km?.toFixed(2)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Trip Efficiency:</span>
            <span class="detail-value">${trip.trip_efficiency?.toFixed(2)}%</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Passengers:</span>
            <span class="detail-value">${trip.passenger_count}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Payment Type:</span>
            <span class="detail-value">${trip.payment_type_name || 'Unknown'}</span>
        </div>
    `;
    
    modal?.classList.add('active');
}

// Make function globally accessible
window.showTripDetails = showTripDetails;

// ==========================================
// CHART INITIALIZATION
// ==========================================
function initializeCharts() {
    // Hourly Trips Chart
    const hourlyCtx = document.getElementById('hourly-trips-chart');
    if (hourlyCtx) {
        AppState.charts.hourly = new Chart(hourlyCtx, {
            type: 'bar',
            data: {
                labels: Array.from({length: 24}, (_, i) => `${i}:00`),
                datasets: [{
                    label: 'Number of Trips',
                    data: [],
                    backgroundColor: 'rgba(255, 193, 7, 0.8)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true },
                    x: { ticks: { maxRotation: 45, minRotation: 45 } }
                }
            }
        });
    }
    
    // Payment Distribution Chart
    const paymentCtx = document.getElementById('payment-chart');
    if (paymentCtx) {
        AppState.charts.payment = new Chart(paymentCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgba(255, 193, 7, 0.9)',
                        'rgba(59, 130, 246, 0.9)',
                        'rgba(16, 185, 129, 0.9)',
                        'rgba(239, 68, 68, 0.9)'
                    ],
                    borderWidth: 3,
                    borderColor: '#FFFFFF'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 15 }
                    }
                }
            }
        });
    }
    
    updateCharts();
}

function updateCharts() {
    if (!AppState.summary) return;
    
    // Update Hourly Chart
    if (AppState.charts.hourly && AppState.summary.hourly_distribution) {
        const hourlyData = Array(24).fill(0);
        AppState.summary.hourly_distribution.forEach(item => {
            hourlyData[item.pickup_hour] = item.trip_count;
        });
        
        AppState.charts.hourly.data.datasets[0].data = hourlyData;
        AppState.charts.hourly.update();
    }
    
    // Update Payment Distribution Chart
    if (AppState.charts.payment && AppState.summary.payment_distribution) {
        const labels = AppState.summary.payment_distribution.map(p => p.payment_type_name);
        const data = AppState.summary.payment_distribution.map(p => p.count);
        
        AppState.charts.payment.data.labels = labels;
        AppState.charts.payment.data.datasets[0].data = data;
        AppState.charts.payment.update();
    }
}

// ==========================================
// MAP FUNCTIONALITY
// ==========================================
function initializeMap() {
    const mapElement = document.getElementById('trip-map');
    if (!mapElement) return;
    
    AppState.map = L.map('trip-map').setView([40.7580, -73.9855], 12);
    AppState.mapRenderer = L.canvas({ padding: 0.5 });
    AppState.mapLayerGroup = L.layerGroup().addTo(AppState.map);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(AppState.map);
    
    updateMap();
}

function setMapMode(mode) {
    AppState.mapMode = mode;
    
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`show-${mode}`)?.classList.add('active');
    
    updateMap();
}

function updateMap() {
    if (!AppState.map) return;
    
    if (AppState.mapLayerGroup) {
        AppState.mapLayerGroup.clearLayers();
    }
    AppState.mapMarkers = [];
    
    const tripsToShow = AppState.allTrips.slice(0, AppState.mapLimit);
    
    if (AppState.mapMode === 'pickups') {
        showPickupMarkers(tripsToShow);
    } else if (AppState.mapMode === 'dropoffs') {
        showDropoffMarkers(tripsToShow);
    } else if (AppState.mapMode === 'heatmap') {
        showTripRoutes(tripsToShow);
    }

    updateZoneLayer();
}

function showPickupMarkers(trips) {
    trips.forEach(trip => {
        if (!trip.pickup_latitude || !trip.pickup_longitude) return;
        
        const marker = L.circleMarker([trip.pickup_latitude, trip.pickup_longitude], {
            radius: 6,
            fillColor: '#FFC107',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.7,
            renderer: AppState.mapRenderer
        }).addTo(AppState.mapLayerGroup);
        
        marker.bindPopup(`
            <div>
                <h4>Pickup Location</h4>
                <p><strong>Time:</strong> ${formatDateTime(trip.pickup_datetime)}</p>
                <p><strong>Fare:</strong> $${trip.fare_amount?.toFixed(2)}</p>
                <p><strong>Distance:</strong> ${trip.trip_distance_km?.toFixed(2)} km</p>
            </div>
        `);
        
        AppState.mapMarkers.push(marker);
    });
}

function showDropoffMarkers(trips) {
    trips.forEach(trip => {
        if (!trip.dropoff_latitude || !trip.dropoff_longitude) return;
        
        const marker = L.circleMarker([trip.dropoff_latitude, trip.dropoff_longitude], {
            radius: 6,
            fillColor: '#3B82F6',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.7,
            renderer: AppState.mapRenderer
        }).addTo(AppState.mapLayerGroup);
        
        marker.bindPopup(`
            <div>
                <h4>Dropoff Location</h4>
                <p><strong>Time:</strong> ${formatDateTime(trip.dropoff_datetime)}</p>
                <p><strong>Fare:</strong> $${trip.fare_amount?.toFixed(2)}</p>
            </div>
        `);
        
        AppState.mapMarkers.push(marker);
    });
}

function showTripRoutes(trips) {
    trips.forEach(trip => {
        if (!trip.pickup_latitude || !trip.pickup_longitude || 
            !trip.dropoff_latitude || !trip.dropoff_longitude) return;
        
        const line = L.polyline(
            [[trip.pickup_latitude, trip.pickup_longitude],
             [trip.dropoff_latitude, trip.dropoff_longitude]],
            { color: '#10B981', weight: 2, opacity: 0.5, renderer: AppState.mapRenderer }
        ).addTo(AppState.mapLayerGroup);
        
        line.bindPopup(`
            <div>
                <h4>Trip Route</h4>
                <p><strong>Distance:</strong> ${trip.trip_distance_km?.toFixed(2)} km</p>
                <p><strong>Duration:</strong> ${formatDuration(Math.round(trip.trip_duration_sec / 60))}</p>
                <p><strong>Fare:</strong> $${trip.fare_amount?.toFixed(2)}</p>
            </div>
        `);
        
        AppState.mapMarkers.push(line);
    });
}

function populateBoroughSelects() {
    const pickupBorough = document.getElementById('pickup-borough-filter');
    const dropoffBorough = document.getElementById('dropoff-borough-filter');
    if (pickupBorough) {
        pickupBorough.innerHTML = '<option value="all">All Boroughs</option>';
        AppState.boroughs.forEach(borough => {
            const option = document.createElement('option');
            option.value = borough;
            option.textContent = borough;
            pickupBorough.appendChild(option);
        });
    }
    if (dropoffBorough) {
        dropoffBorough.innerHTML = '<option value="all">All Boroughs</option>';
        AppState.boroughs.forEach(borough => {
            const option = document.createElement('option');
            option.value = borough;
            option.textContent = borough;
            dropoffBorough.appendChild(option);
        });
    }
}

function populateZoneSelects() {
    updateZoneOptions('pickup-zone-filter', null);
    updateZoneOptions('dropoff-zone-filter', null);
}

function updateZoneOptions(selectId, borough) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    select.innerHTML = '<option value="all">All Zones</option>';
    let index = 0;
    while (index < AppState.zones.length) {
        const zone = AppState.zones[index];
        const matchBorough = !borough || borough === 'all' || zone.borough === borough;
        if (matchBorough) {
            const option = document.createElement('option');
            option.value = zone.zone;
            option.textContent = zone.zone;
            select.appendChild(option);
        }
        index += 1;
    }
}

async function updateZoneLayer() {
    if (!AppState.map) return;
    
    if (!AppState.zoneLayerVisible) {
        if (AppState.zoneLayer) {
            AppState.map.removeLayer(AppState.zoneLayer);
            AppState.zoneLayer = null;
        }
        AppState.zoneLayerKey = null;
        return;
    }
    
    const sourceGeoJson = AppState.zonesGeoJson;
    if (!sourceGeoJson || !Array.isArray(sourceGeoJson.features)) {
        return;
    }

    const boroughFilter = AppState.filters.pickup_borough || AppState.filters.dropoff_borough;
    const zoneFilter = AppState.filters.pickup_zone || AppState.filters.dropoff_zone;
    const zoneLayerKey = `${boroughFilter || ''}|${zoneFilter || ''}`;
    if (AppState.zoneLayer && AppState.zoneLayerKey === zoneLayerKey) {
        return;
    }
    const filteredFeatures = [];

    let index = 0;
    while (index < sourceGeoJson.features.length) {
        const feature = sourceGeoJson.features[index];
        const props = feature.properties || {};
        const boroughMatch = !boroughFilter || props.borough === boroughFilter;
        const zoneMatch = !zoneFilter || props.zone === zoneFilter;
        if (boroughMatch && zoneMatch) {
            filteredFeatures.push(feature);
        }
        index += 1;
    }

    if (AppState.zoneLayer) {
        AppState.map.removeLayer(AppState.zoneLayer);
    }

    AppState.zoneLayer = L.geoJSON({
        type: 'FeatureCollection',
        features: filteredFeatures
    }, {
        style: {
            color: '#111827',
            weight: 1,
            opacity: 0.6,
            fillColor: '#60A5FA',
            fillOpacity: 0.1
        }
    }).addTo(AppState.map);
    AppState.zoneLayerKey = zoneLayerKey;
}

// ==========================================
// EXPORT FUNCTIONALITY
// ==========================================
function exportToCSV() {
    const headers = [
        'Trip ID', 'Pickup DateTime', 'Dropoff DateTime',
        'Distance (km)', 'Duration (min)', 'Fare ($)', 'Tip ($)', 'Total ($)',
        'Passengers', 'Payment Type'
    ];
    
    const rows = AppState.allTrips.map(trip => [
        getTripId(trip),
        trip.pickup_datetime,
        trip.dropoff_datetime,
        trip.trip_distance_km,
        Math.round(trip.trip_duration_sec / 60),
        trip.fare_amount,
        trip.tip_amount,
        trip.total_amount,
        trip.passenger_count,
        trip.payment_type_name || ''
    ]);
    
    const csv = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nyc_taxi_trips_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================
function showErrorMessage(message) {
    alert(message);
}

console.log('NYC Urban Mobility Explorer - Ready!');

