<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { authStore, bicycleStore, riskScoreStore, notifications } from '$lib/stores.js';
    import { bicyclesApi, riskApi } from '$lib/api.js';
    import RiskBadge from '$lib/components/RiskBadge.svelte';

    let bicycles = [];
    let filteredBikes = [];
    let statusFilter = '';
    let searchQuery = '';
    let showAddForm = false;
    let loading = true;

    // Add form
    let newBike = { bike_code: '', make: '', model: '', year: '', color: '', condition: 'Good', location: '', purchase_date: '' };

    let riskScores = {};

    onMount(async () => {
        if (!$authStore.isAuthenticated) { goto('/login'); return; }
        await loadBicycles();
    });

    async function loadBicycles() {
        loading = true;
        try {
            const [bikesRes, riskRes] = await Promise.all([
                bicyclesApi.getAll(),
                riskApi.getAll().catch(() => ({ risk_scores: [] }))
            ]);
            bicycles = bikesRes.bicycles || [];
            bicycleStore.refresh(bicycles);

            const scores = riskRes.risk_scores || [];
            riskScoreStore.setScores(scores);
            scores.forEach(s => { riskScores[s.bicycle_id] = s; });
            riskScores = riskScores;

            applyFilters();
        } catch (err) {
            notifications.add('Failed to load bicycles', 'error');
        } finally {
            loading = false;
        }
    }

    function applyFilters() {
        filteredBikes = bicycles.filter(b => {
            const matchStatus = !statusFilter || b.status === statusFilter;
            const matchSearch = !searchQuery || b.bike_code.toLowerCase().includes(searchQuery.toLowerCase()) || b.make.toLowerCase().includes(searchQuery.toLowerCase()) || b.model.toLowerCase().includes(searchQuery.toLowerCase());
            return matchStatus && matchSearch;
        });
    }

    $: statusFilter, searchQuery, applyFilters();

    async function addBicycle() {
        try {
            const data = { ...newBike };
            if (data.year) data.year = parseInt(data.year);
            else delete data.year;
            if (!data.purchase_date) delete data.purchase_date;

            await bicyclesApi.create(data);
            notifications.add('Bicycle added successfully!', 'success');
            showAddForm = false;
            newBike = { bike_code: '', make: '', model: '', year: '', color: '', condition: 'Good', location: '', purchase_date: '' };
            await loadBicycles();
        } catch (err) {
            notifications.add(err.message || 'Failed to add bicycle', 'error');
        }
    }

    async function updateStatus(bikeId, status) {
        try {
            await bicyclesApi.updateStatus(bikeId, status);
            notifications.add(`Status updated to ${status}`, 'success');
            await loadBicycles();
        } catch (err) {
            notifications.add(err.message || 'Failed to update status', 'error');
        }
    }

    function getStatusBadge(status) {
        const map = { 'Available': 'badge-green', 'Rented': 'badge-blue', 'In Maintenance': 'badge-yellow', 'Out of Service': 'badge-red' };
        return map[status] || 'badge-gray';
    }
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
            <h1 class="text-3xl font-bold text-gray-800">Bicycles</h1>
            <p class="text-gray-500">Manage your fleet</p>
        </div>
        <button on:click={() => showAddForm = !showAddForm} class="btn btn-primary">
            {showAddForm ? 'Cancel' : '+ Add Bicycle'}
        </button>
    </div>

    <!-- Add Form -->
    {#if showAddForm}
        <div class="card mb-6">
            <h3 class="text-lg font-semibold mb-4">Register New Bicycle</h3>
            <form on:submit|preventDefault={addBicycle} class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Bike Code *</label>
                    <input bind:value={newBike.bike_code} class="input" placeholder="BIKE-001" required />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Make *</label>
                    <input bind:value={newBike.make} class="input" placeholder="Trek" required />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Model *</label>
                    <input bind:value={newBike.model} class="input" placeholder="FX 3" required />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Year</label>
                    <input bind:value={newBike.year} class="input" type="number" placeholder="2024" />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Color</label>
                    <input bind:value={newBike.color} class="input" placeholder="Blue" />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Condition</label>
                    <select bind:value={newBike.condition} class="input">
                        <option>Good</option><option>Fair</option><option>Poor</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Location</label>
                    <input bind:value={newBike.location} class="input" placeholder="Station A" />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Purchase Date</label>
                    <input bind:value={newBike.purchase_date} class="input" type="date" />
                </div>
                <div class="flex items-end">
                    <button type="submit" class="btn btn-success w-full">Register Bicycle</button>
                </div>
            </form>
        </div>
    {/if}

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <input bind:value={searchQuery} class="input max-w-xs" placeholder="Search bikes..." />
        <select bind:value={statusFilter} class="input max-w-xs">
            <option value="">All Statuses</option>
            <option>Available</option>
            <option>Rented</option>
            <option>In Maintenance</option>
            <option>Out of Service</option>
        </select>
    </div>

    {#if loading}
        <div class="flex justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
    {:else if filteredBikes.length === 0}
        <div class="text-center py-20 text-gray-400">
            <p class="text-4xl mb-4">🚲</p>
            <p>No bicycles found. Add your first bike!</p>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each filteredBikes as bike (bike.id)}
                <div class="card hover:shadow-md transition-shadow">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h3 class="font-bold text-lg">{bike.bike_code}</h3>
                            <p class="text-sm text-gray-500">{bike.make} {bike.model}</p>
                        </div>
                        <div class="flex flex-col items-end gap-1">
                            <span class="badge {getStatusBadge(bike.status)}">{bike.status}</span>
                            {#if riskScores[bike.id]}
                                <RiskBadge
                                    score={riskScores[bike.id].score}
                                    level={riskScores[bike.id].risk_level}
                                    showTooltip={true}
                                    featureImportance={riskScores[bike.id].feature_importance}
                                />
                            {/if}
                        </div>
                    </div>

                    <div class="text-sm text-gray-600 space-y-1 mb-4">
                        {#if bike.color}<p>Color: {bike.color}</p>{/if}
                        {#if bike.condition}<p>Condition: {bike.condition}</p>{/if}
                        {#if bike.location}<p>Location: {bike.location}</p>{/if}
                        {#if bike.total_rentals}<p>Total Rentals: {bike.total_rentals}</p>{/if}
                    </div>

                    <div class="flex flex-wrap gap-2">
                        <a href="/bicycles/{bike.id}" class="btn btn-outline text-xs">Details</a>
                        {#if bike.status === 'Available'}
                            <button on:click={() => updateStatus(bike.id, 'Out of Service')} class="btn btn-warning text-xs">Out of Service</button>
                        {/if}
                        {#if bike.status === 'In Maintenance' || bike.status === 'Out of Service'}
                            <button on:click={() => updateStatus(bike.id, 'Available')} class="btn btn-success text-xs">Mark Available</button>
                        {/if}
                        <a href="/assistant?bike_id={bike.id}" class="btn btn-outline text-xs">🤖 Ask about this bike</a>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

