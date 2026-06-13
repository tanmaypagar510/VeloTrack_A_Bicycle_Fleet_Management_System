import { browser } from '$app/environment';

const API_BASE = browser ? (window.location.port === '3000' ? 'http://localhost:8080' : '') : 'http://nginx:80';

function getToken() {
    if (browser) {
        return localStorage.getItem('token') || '';
    }
    return '';
}

async function request(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        if (!response.ok) {
            throw { status: response.status, message: `Server error (${response.status}). Please try again.` };
        }
        throw { status: response.status, message: 'Unexpected response from server.' };
    }

    const data = await response.json();
    if (!response.ok) {
        throw { status: response.status, message: data.error || 'Request failed', data };
    }
    return data;
}

// Auth API
export const authApi = {
    login: (email, password) => request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
    register: (data) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    me: () => request('/api/auth/me'),
    changePassword: (current_password, new_password) => request('/api/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password, new_password }) })
};

// Bicycles API
export const bicyclesApi = {
    getAll: (status) => request(`/api/bicycles/${status ? `?status=${status}` : ''}`),
    getById: (id) => request(`/api/bicycles/${id}`),
    create: (data) => request('/api/bicycles/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => request(`/api/bicycles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    updateStatus: (id, status) => request(`/api/bicycles/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
    delete: (id) => request(`/api/bicycles/${id}`, { method: 'DELETE' })
};

// Maintenance API
export const maintenanceApi = {
    getAll: (bicycleId) => request(`/api/maintenance/${bicycleId ? `?bicycle_id=${bicycleId}` : ''}`),
    getById: (id) => request(`/api/maintenance/${id}`),
    create: (data) => request('/api/maintenance/', { method: 'POST', body: JSON.stringify(data) }),
    getHistory: (bicycleId) => request(`/api/maintenance/history/${bicycleId}`)
};

// Rentals API
export const rentalsApi = {
    getAll: (bicycleId, status) => {
        let params = [];
        if (bicycleId) params.push(`bicycle_id=${bicycleId}`);
        if (status) params.push(`status=${status}`);
        return request(`/api/rentals/${params.length ? '?' + params.join('&') : ''}`);
    },
    checkout: (data) => request('/api/rentals/checkout', { method: 'POST', body: JSON.stringify(data) }),
    return: (rentalId) => request(`/api/rentals/return/${rentalId}`, { method: 'POST' }),
    getById: (id) => request(`/api/rentals/${id}`)
};

// Maintenance Assistant API
export const assistantApi = {
    ask: (question, bike_id) => request('/api/maintenance-assistant/ask', { method: 'POST', body: JSON.stringify({ question, bike_id: bike_id || undefined }) }),
    getHistory: () => request('/api/maintenance-assistant/history')
};

// Risk Scores API
export const riskApi = {
    getAll: () => request('/api/risk-scores/'),
    getByBike: (bikeId) => request(`/api/risk-scores/${bikeId}`),
    retrain: () => request('/api/risk-scores/retrain', { method: 'POST' }),
    batchUpdate: () => request('/api/risk-scores/batch-update', { method: 'POST' })
};

