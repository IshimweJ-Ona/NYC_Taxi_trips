const API_BASE_URL = 'http://127.0.0.1:5000/api';

let currentState = {
    page: 1,
    per_page: 20,
    filters: {}
};

const tripsTableBody = document.getElementById('trips-table-body');
const totalTripsEl = document.getElementById('total-trips');
const avgFareEl = document.getElementById('avg-fare');
const avgSpeedEl = document.getElementById('avg-speed');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageInfoEl = document.getElementById('page-info');
const filterForm = document.getElementById('filter-form');

document.addEventListener('DOMContentLoaded', () => {
    fetchTrips();
    fetchSummary();
});

filterForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(filterForm);
    currentState.filters = Object.fromEntries(formData.entries());
    currentState.page = 1;
    fetchTrips();
    fetchSummary();
});

prevPageBtn.addEventListener('click', () => {
    if (currentState.page > 1) {
        currentState.page--;
        fetchTrips();
    }
});

nextPageBtn.addEventListener('click', () => {
    currentState.page++;
    fetchTrips();
});

async function fetchTrips() {
    const params = new URLSearchParams({
        page: currentState.page,
        per_page: currentState.per_page,
        ...currentState.filters
    });

    try {
        const response = await fetch(`${API_BASE_URL}/trips?${params}`);
        const data = await response.json();

        renderTable(data.data);
        updatePagination(data.pagination);
    } catch (error) {
        console.error('Error fetching trips:', error);
        tripsTableBody.innerHTML = '<tr><td colspan="5">Error loading data</td></tr>';
    }
}

async function fetchSummary() {
    const params = new URLSearchParams(currentState.filters);
    try {
        const response = await fetch(`${API_BASE_URL}/summary?${params}`);
        const data = await response.json();
        renderSummary(data);
    } catch (error) {
        console.error('Error fetching summary:', error);
    }
}

function renderTable(trips) {
    tripsTableBody.innerHTML = '';

    if (!trips || trips.length === 0) {
        tripsTableBody.innerHTML = '<tr><td colspan="5">No trips found</td></tr>';
        return;
    }

    trips.forEach(trip => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(trip.pickup_datetime).toLocaleString()}</td>
            <td>${parseFloat(trip.trip_distance_km).toFixed(2)}</td>
            <td>$${parseFloat(trip.fare_amount).toFixed(2)}</td>
            <td>$${parseFloat(trip.tip_amount).toFixed(2)}</td>
            <td>${trip.trip_efficiency ? parseFloat(trip.trip_efficiency).toFixed(2) : '-'}</td>
        `;
        tripsTableBody.appendChild(row);
    });
}

function renderSummary(data) {
    totalTripsEl.textContent = data.total_trips || 0;
    avgFareEl.textContent = `$${parseFloat(data.avg_fare || 0).toFixed(2)}`;
    avgSpeedEl.textContent = `${parseFloat(data.avg_speed_kmh || 0).toFixed(1)}`;
}

function updatePagination(pagination) {
    pageInfoEl.textContent = `Page ${pagination.page} of ${pagination.total_pages || 1}`;
    prevPageBtn.disabled = pagination.page <= 1;
    nextPageBtn.disabled = pagination.page >= pagination.total_pages;
}
