import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Auth Store
function createAuthStore() {
    const initial = {
        token: browser ? localStorage.getItem('token') : null,
        user: browser ? JSON.parse(localStorage.getItem('user') || 'null') : null,
        isAuthenticated: browser ? !!localStorage.getItem('token') : false
    };

    const { subscribe, set, update } = writable(initial);

    return {
        subscribe,
        login: (token, user) => {
            if (browser) {
                localStorage.setItem('token', token);
                localStorage.setItem('user', JSON.stringify(user));
            }
            set({ token, user, isAuthenticated: true });
        },
        logout: () => {
            if (browser) {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
            }
            set({ token: null, user: null, isAuthenticated: false });
        },
        updateUser: (user) => {
            if (browser) {
                localStorage.setItem('user', JSON.stringify(user));
            }
            update(state => ({ ...state, user }));
        }
    };
}

// Bicycle Store
function createBicycleStore() {
    const { subscribe, set, update } = writable([]);
    return {
        subscribe,
        set,
        update,
        refresh: (bicycles) => set(bicycles)
    };
}

// Risk Score Store
function createRiskScoreStore() {
    const { subscribe, set, update } = writable({});
    return {
        subscribe,
        set,
        setScores: (scores) => {
            const map = {};
            scores.forEach(s => { map[s.bicycle_id] = s; });
            set(map);
        },
        updateScore: (bikeId, score) => {
            update(state => ({ ...state, [bikeId]: score }));
        }
    };
}

// Notification Store
function createNotificationStore() {
    const { subscribe, update } = writable([]);

    let id = 0;
    return {
        subscribe,
        add: (message, type = 'info') => {
            const notification = { id: ++id, message, type };
            update(n => [...n, notification]);
            setTimeout(() => {
                update(n => n.filter(x => x.id !== notification.id));
            }, 4000);
        },
        remove: (id) => {
            update(n => n.filter(x => x.id !== id));
        }
    };
}

export const authStore = createAuthStore();
export const bicycleStore = createBicycleStore();
export const riskScoreStore = createRiskScoreStore();
export const notifications = createNotificationStore();

