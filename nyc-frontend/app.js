// ==========================================
// NYC URBAN MOBILITY EXPLORER
// Frontend Application - Integrated with Backend API
// ==========================================

// API Configuration
const API_BASE = 'http://localhost:5000';

// Global State Management
const AppState = {
    allTrips: [],
    currentPage: 1,
    tripsPerPage: 50,
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
        payment_type: null
    },
    charts: {},
    map: null,
    mapMarkers: [],
    mapMode: 'pickups',
    mapLimit: 100,
    useCustomSort: false,
    summary: null
};

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
        
        await Promise.all([
            fetchTrips(),
            fetchSummary()
        ]);
        
        updateDashboard();
        
        console.log(`✓ Loaded ${AppState.totalTrips.toLocaleString()} total trips`);
        
    } catch (error) {
        console.error('Error initializing app:', error);
        showErrorMessage('Failed to load data. Please check backend connection.');
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
        
        // Add filters
        Object.entries(AppState.filters).forEach(([key, value]) => {
            if (value !== null && value !== '' && value !== 'all') {
                params.append(key, value);
            }
        });
        
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
    
    // Reset to page 1
    AppState.currentPage = 1;
    
    // Fetch new data
    await fetchTrips(1);
    await fetchSummary();
    
    // Update UI
    updateDashboard();
}

function resetFilters() {
    // Reset controls
    if (document.getElementById('min-distance')) document.getElementById('min-distance').value = 0;
    if (document.getElementById('max-distance')) document.getElementById('max-distance').value = 100;
    if (document.getElementById('min-fare')) document.getElementById('min-fare').value = 0;
    if (document.getElementById('max-fare')) document.getElementById('max-fare').value = 200;
    if (document.getElementById('peak-filter')) document.getElementById('peak-filter').value = 'all';
    if (document.getElementById('weekend-filter')) document.getElementById('weekend-filter').value = 'all';
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
        payment_type: null
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
            <button onclick="showTripDetails(${trip.trip_id})">View</button>
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
    const newPage = AppState.currentPage + delta;
    
    if (newPage >= 1 && newPage <= AppState.totalPages) {
        await goToPage(newPage);
    }
}

async function goToPage(page) {
    AppState.currentPage = page;
    await fetchTrips(page);
    updateDashboard();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// TRIP DETAILS MODAL
// ==========================================
function showTripDetails(tripId) {
    const trip = AppState.allTrips.find(t => t.trip_id === tripId);
    if (!trip) return;
    
    const modal = document.getElementById('trip-modal');
    const modalBody = document.getElementById('modal-body');
    
    if (!modalBody) return;
    
    const durationMinutes = Math.round(trip.trip_duration_sec / 60);
    
    modalBody.innerHTML = `
        <div class="detail-row">
            <span class="detail-label">Trip ID:</span>
            <span class="detail-value">#${trip.trip_id}</span>
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
    
    // Clear old markers
    AppState.mapMarkers.forEach(marker => {
        AppState.map.removeLayer(marker);
    });
    AppState.mapMarkers = [];
    
    const tripsToShow = AppState.allTrips.slice(0, AppState.mapLimit);
    
    if (AppState.mapMode === 'pickups') {
        showPickupMarkers(tripsToShow);
    } else if (AppState.mapMode === 'dropoffs') {
        showDropoffMarkers(tripsToShow);
    } else if (AppState.mapMode === 'heatmap') {
        showTripRoutes(tripsToShow);
    }
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
            fillOpacity: 0.7
        }).addTo(AppState.map);
        
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
            fillOpacity: 0.7
        }).addTo(AppState.map);
        
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
            { color: '#10B981', weight: 2, opacity: 0.5 }
        ).addTo(AppState.map);
        
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
        trip.trip_id,
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
