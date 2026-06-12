<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { authStore, bicycleStore, riskScoreStore, notifications } from '$lib/stores.js';
    import { bicyclesApi, riskApi, rentalsApi, maintenanceApi } from '$lib/api.js';
    import RiskBadge from '$lib/components/RiskBadge.svelte';

    let stats = { total: 0, available: 0, rented: 0, maintenance: 0, outOfService: 0 };
    let highRiskCount = 0;
    let totalBikes = 0;
    let showHighRiskAlert = true;
    let recentRentals = [];
    let recentMaintenance = [];
    let loading = true;

    onMount(async () => {
        if (!$authStore.isAuthenticated) { goto('/login'); return; }

        try {
            const [bikesRes, riskRes, rentalsRes, maintRes] = await Promise.all([
                bicyclesApi.getAll(),
                riskApi.getAll().catch(() => ({ risk_scores: [] })),
                rentalsApi.getAll().catch(() => ({ rentals: [] })),
                maintenanceApi.getAll().catch(() => ({ maintenance_logs: [] }))
            ]);

            const bikes = bikesRes.bicycles || [];
            bicycleStore.refresh(bikes);
            totalBikes = bikes.length;

            stats = {
                total: bikes.length,
                available: bikes.filter(b => b.status === 'Available').length,
                rented: bikes.filter(b => b.status === 'Rented').length,
                maintenance: bikes.filter(b => b.status === 'In Maintenance').length,
                outOfService: bikes.filter(b => b.status === 'Out of Service').length
            };

            const scores = riskRes.risk_scores || [];
            riskScoreStore.setScores(scores);
            highRiskCount = scores.filter(s => s.risk_level === 'High').length;

            recentRentals = (rentalsRes.rentals || []).slice(0, 5);
            recentMaintenance = (maintRes.maintenance_logs || []).slice(0, 5);
        } catch (err) {
            notifications.add('Failed to load dashboard data', 'error');
        } finally {
            loading = false;
        }
    });
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800">Dashboard</h1>
        <p class="text-gray-500 mt-1">Fleet overview and quick actions</p>
    </div>

    <!-- High Risk Alert Banner -->
    {#if showHighRiskAlert && totalBikes > 0 && highRiskCount / totalBikes > 0.2}
        <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center justify-between">
            <div class="flex items-center">
                <span class="text-2xl mr-3">⚠️</span>
                <div>
                    <p class="font-semibold text-red-800">High Risk Alert</p>
                    <p class="text-red-600 text-sm">{highRiskCount} of {totalBikes} bikes ({Math.round(highRiskCount/totalBikes*100)}%) are in High risk tier. Review the fleet immediately.</p>
                </div>
            </div>
            <button on:click={() => showHighRiskAlert = false} class="text-red-400 hover:text-red-600 text-xl">✕</button>
        </div>
    {/if}

    {#if loading}
        <div class="flex justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
    {:else}
        <!-- Stats Cards -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div class="card text-center">
                <p class="text-3xl font-bold text-primary-600">{stats.total}</p>
                <p class="text-sm text-gray-500">Total Bikes</p>
            </div>
            <div class="card text-center">
                <p class="text-3xl font-bold text-green-600">{stats.available}</p>
                <p class="text-sm text-gray-500">Available</p>
            </div>
            <div class="card text-center">
                <p class="text-3xl font-bold text-blue-600">{stats.rented}</p>
                <p class="text-sm text-gray-500">Rented</p>
            </div>
            <div class="card text-center">
                <p class="text-3xl font-bold text-yellow-600">{stats.maintenance}</p>
                <p class="text-sm text-gray-500">In Maintenance</p>
            </div>
            <div class="card text-center">
                <p class="text-3xl font-bold text-red-600">{stats.outOfService}</p>
                <p class="text-sm text-gray-500">Out of Service</p>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="grid md:grid-cols-4 gap-4 mb-8">
            <a href="/bicycles?action=add" class="card hover:shadow-md transition-shadow text-center">
                <span class="text-3xl">➕</span>
                <p class="font-medium mt-2">Add Bicycle</p>
            </a>
            <a href="/rentals?action=checkout" class="card hover:shadow-md transition-shadow text-center">
                <span class="text-3xl">🔑</span>
                <p class="font-medium mt-2">New Rental</p>
            </a>
            <a href="/maintenance?action=add" class="card hover:shadow-md transition-shadow text-center">
                <span class="text-3xl">🔧</span>
                <p class="font-medium mt-2">Log Maintenance</p>
            </a>
            <a href="/assistant" class="card hover:shadow-md transition-shadow text-center">
                <span class="text-3xl">🤖</span>
                <p class="font-medium mt-2">Ask Assistant</p>
            </a>
        </div>

        <!-- Recent Activity -->
        <div class="grid md:grid-cols-2 gap-6">
            <div class="card">
                <h3 class="text-lg font-semibold mb-4">Recent Rentals</h3>
                {#if recentRentals.length === 0}
                    <p class="text-gray-400 text-sm">No rentals yet</p>
                {:else}
                    <div class="space-y-3">
                        {#each recentRentals as rental}
                            <div class="flex justify-between items-center border-b pb-2">
                                <div>
                                    <p class="text-sm font-medium">Bike #{rental.bicycle_id} - {rental.renter_name}</p>
                                    <p class="text-xs text-gray-500">{new Date(rental.checkout_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})}</p>
                                </div>
                                <span class="badge {rental.status === 'Active' ? 'badge-blue' : 'badge-green'}">{rental.status}</span>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>

            <div class="card">
                <h3 class="text-lg font-semibold mb-4">Recent Maintenance</h3>
                {#if recentMaintenance.length === 0}
                    <p class="text-gray-400 text-sm">No maintenance logs yet</p>
                {:else}
                    <div class="space-y-3">
                        {#each recentMaintenance as log}
                            <div class="flex justify-between items-center border-b pb-2">
                                <div>
                                    <p class="text-sm font-medium">Bike #{log.bicycle_id}</p>
                                    <p class="text-xs text-gray-500">{log.problem_description?.substring(0, 50)}</p>
                                </div>
                                <span class="text-xs text-gray-400">{new Date(log.service_date).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})}</span>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>

