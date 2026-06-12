<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { authStore, notifications } from '$lib/stores.js';
    import { bicyclesApi, maintenanceApi, riskApi } from '$lib/api.js';
    import RiskBadge from '$lib/components/RiskBadge.svelte';
    import RiskSparkline from '$lib/components/RiskSparkline.svelte';

    let bike = null;
    let history = { maintenance_logs: [], rentals: [] };
    let riskData = null;
    let trendData = [];
    let loading = true;

    $: bikeId = $page.params.id;

    onMount(async () => {
        if (!$authStore.isAuthenticated) { goto('/login'); return; }
        await loadBikeDetails();
    });

    async function loadBikeDetails() {
        loading = true;
        try {
            const [bikeRes, historyRes, riskRes] = await Promise.all([
                bicyclesApi.getById(bikeId),
                maintenanceApi.getHistory(bikeId).catch(() => ({ maintenance_logs: [], rentals: [] })),
                riskApi.getByBike(bikeId).catch(() => null)
            ]);
            bike = bikeRes.bicycle;
            history = historyRes;
            if (riskRes) {
                riskData = riskRes.risk_score;
                trendData = riskRes.trend || [];
            }
        } catch (err) {
            notifications.add('Failed to load bike details', 'error');
        } finally {
            loading = false;
        }
    }

    function getStatusBadge(status) {
        const map = { 'Available': 'badge-green', 'Rented': 'badge-blue', 'In Maintenance': 'badge-yellow', 'Out of Service': 'badge-red' };
        return map[status] || 'badge-gray';
    }
</script>

<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <a href="/bicycles" class="text-primary-600 hover:underline text-sm mb-4 inline-block">← Back to Bicycles</a>

    {#if loading}
        <div class="flex justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
    {:else if bike}
        <div class="card mb-6">
            <div class="flex justify-between items-start">
                <div>
                    <h1 class="text-3xl font-bold">{bike.bike_code}</h1>
                    <p class="text-gray-500 text-lg">{bike.make} {bike.model} {bike.year || ''}</p>
                </div>
                <div class="flex flex-col items-end gap-2">
                    <span class="badge {getStatusBadge(bike.status)} text-sm">{bike.status}</span>
                    {#if riskData}
                        <RiskBadge score={riskData.score} level={riskData.risk_level} showTooltip={true} featureImportance={riskData.feature_importance} />
                    {/if}
                </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                <div><p class="text-xs text-gray-500 uppercase">Color</p><p class="font-medium">{bike.color || 'N/A'}</p></div>
                <div><p class="text-xs text-gray-500 uppercase">Condition</p><p class="font-medium">{bike.condition}</p></div>
                <div><p class="text-xs text-gray-500 uppercase">Location</p><p class="font-medium">{bike.location || 'N/A'}</p></div>
                <div><p class="text-xs text-gray-500 uppercase">Purchase Date</p><p class="font-medium">{bike.purchase_date || 'N/A'}</p></div>
                <div><p class="text-xs text-gray-500 uppercase">Total Rentals</p><p class="font-medium">{bike.total_rentals}</p></div>
                <div><p class="text-xs text-gray-500 uppercase">Last Serviced</p><p class="font-medium">{bike.last_serviced ? new Date(bike.last_serviced).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) : 'Never'}</p></div>
                <div>
                    <p class="text-xs text-gray-500 uppercase">Risk Trend (30d)</p>
                    <RiskSparkline data={trendData} />
                </div>
            </div>

            <div class="mt-4 flex gap-2">
                <a href="/assistant?bike_id={bike.id}" class="btn btn-primary text-sm">🤖 Ask about this bike</a>
            </div>
        </div>

        <!-- Maintenance History -->
        <div class="card mb-6">
            <h2 class="text-xl font-semibold mb-4">Maintenance History ({history.total_maintenance || history.maintenance_logs?.length || 0})</h2>
            {#if history.maintenance_logs?.length > 0}
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-4 py-2 text-left">Date (IST)</th>
                                <th class="px-4 py-2 text-left">Problem</th>
                                <th class="px-4 py-2 text-left">Work Done</th>
                                <th class="px-4 py-2 text-left">Technician</th>
                                <th class="px-4 py-2 text-right">Cost (₹)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each history.maintenance_logs as log}
                                <tr class="border-t">
                                    <td class="px-4 py-2">{new Date(log.service_date).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})}</td>
                                    <td class="px-4 py-2">{log.problem_description}</td>
                                    <td class="px-4 py-2">{log.work_done}</td>
                                    <td class="px-4 py-2">{log.technician}</td>
                                    <td class="px-4 py-2 text-right">₹{log.cost}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            {:else}
                <p class="text-gray-400">No maintenance records</p>
            {/if}
        </div>

        <!-- Rental History -->
        <div class="card">
            <h2 class="text-xl font-semibold mb-4">Rental History ({history.total_rentals || history.rentals?.length || 0})</h2>
            {#if history.rentals?.length > 0}
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-4 py-2 text-left">Checkout (IST)</th>
                                <th class="px-4 py-2 text-left">Return (IST)</th>
                                <th class="px-4 py-2 text-left">Renter</th>
                                <th class="px-4 py-2 text-left">Duration</th>
                                <th class="px-4 py-2 text-right">Cost (₹)</th>
                                <th class="px-4 py-2 text-left">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each history.rentals as rental}
                                <tr class="border-t {rental.is_anomalous ? 'bg-red-50' : ''}">
                                    <td class="px-4 py-2">{new Date(rental.checkout_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})}</td>
                                    <td class="px-4 py-2">{rental.return_time ? new Date(rental.return_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) : '—'}</td>
                                    <td class="px-4 py-2">{rental.renter_name}</td>
                                    <td class="px-4 py-2">{rental.duration_hours ? rental.duration_hours + 'h' : '—'}</td>
                                    <td class="px-4 py-2 text-right">{rental.rental_cost ? '₹' + rental.rental_cost : '—'}</td>
                                    <td class="px-4 py-2">
                                        <span class="badge {rental.status === 'Active' ? 'badge-blue' : 'badge-green'}">{rental.status}</span>
                                        {#if rental.is_anomalous}<span class="badge badge-red ml-1">Anomalous</span>{/if}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            {:else}
                <p class="text-gray-400">No rental records</p>
            {/if}
        </div>
    {:else}
        <p class="text-center text-gray-500 py-20">Bicycle not found</p>
    {/if}
</div>

