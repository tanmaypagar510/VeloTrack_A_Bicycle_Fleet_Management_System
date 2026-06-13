<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { authStore, notifications } from '$lib/stores.js';
    import { maintenanceApi, bicyclesApi } from '$lib/api.js';

    let logs = [];
    let bicycles = [];
    let loading = true;
    let showAddForm = false;

    let newLog = { bicycle_id: '', problem_description: '', work_done: '', technician: '', cost: 0 };

    onMount(async () => {
        if (!$authStore.isAuthenticated) { goto('/login'); return; }
        await loadData();
    });

    async function loadData() {
        loading = true;
        try {
            const [logsRes, bikesRes] = await Promise.all([
                maintenanceApi.getAll(),
                bicyclesApi.getAll()
            ]);
            logs = logsRes.maintenance_logs || [];
            bicycles = bikesRes.bicycles || [];
        } catch (err) {
            notifications.add('Failed to load maintenance logs', 'error');
        } finally {
            loading = false;
        }
    }

    async function createLog() {
        try {
            const data = { ...newLog, bicycle_id: parseInt(newLog.bicycle_id), cost: parseFloat(newLog.cost) || 0 };
            await maintenanceApi.create(data);
            notifications.add('Maintenance log created!', 'success');
            showAddForm = false;
            newLog = { bicycle_id: '', problem_description: '', work_done: '', technician: '', cost: 0 };
            await loadData();
        } catch (err) {
            notifications.add(err.message || 'Failed to create log', 'error');
        }
    }

    function getBikeName(bikeId) {
        const bike = bicycles.find(b => b.id === bikeId);
        return bike ? `${bike.bike_code} (${bike.make} ${bike.model})` : `Bike #${bikeId}`;
    }
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex justify-between items-center mb-6">
        <div>
            <h1 class="text-3xl font-bold text-gray-800">Maintenance Logs</h1>
            <p class="text-gray-500">Track all bicycle servicing</p>
        </div>
        <button on:click={() => showAddForm = !showAddForm} class="btn btn-primary">
            {showAddForm ? 'Cancel' : '+ New Log'}
        </button>
    </div>

    {#if showAddForm}
        <div class="card mb-6">
            <h3 class="text-lg font-semibold mb-4">Create Maintenance Log</h3>
            <form on:submit|preventDefault={createLog} class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Bicycle *</label>
                    <select bind:value={newLog.bicycle_id} class="input" required>
                        <option value="">Select a bicycle</option>
                        {#each bicycles.filter(b => b.status !== 'Rented') as bike}
                            <option value={bike.id}>{bike.bike_code} - {bike.make} {bike.model} ({bike.status})</option>
                        {/each}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Technician *</label>
                    <input bind:value={newLog.technician} class="input" placeholder="John Smith" required />
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm font-medium text-gray-700 mb-1">Problem Description *</label>
                    <textarea bind:value={newLog.problem_description} class="input" rows="2" placeholder="Describe the issue..." required></textarea>
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm font-medium text-gray-700 mb-1">Work Done *</label>
                    <textarea bind:value={newLog.work_done} class="input" rows="2" placeholder="What was repaired/replaced..." required></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Cost (₹)</label>
                    <input bind:value={newLog.cost} class="input" type="number" step="0.01" min="0" />
                </div>
                <div class="flex items-end">
                    <button type="submit" class="btn btn-success w-full">Create Log</button>
                </div>
            </form>
        </div>
    {/if}

    {#if loading}
        <div class="flex justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
    {:else if logs.length === 0}
        <div class="text-center py-20 text-gray-400">
            <p class="text-4xl mb-4">🔧</p>
            <p>No maintenance logs yet</p>
        </div>
    {:else}
        <div class="card overflow-x-auto">
            <table class="w-full text-sm">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left">Date (IST)</th>
                        <th class="px-4 py-3 text-left">Bicycle</th>
                        <th class="px-4 py-3 text-left">Problem</th>
                        <th class="px-4 py-3 text-left">Work Done</th>
                        <th class="px-4 py-3 text-left">Technician</th>
                        <th class="px-4 py-3 text-right">Cost (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    {#each logs as log}
                        <tr class="border-t hover:bg-gray-50">
                            <td class="px-4 py-3">{new Date(log.service_date).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})}</td>
                            <td class="px-4 py-3 font-medium">{getBikeName(log.bicycle_id)}</td>
                            <td class="px-4 py-3">{log.problem_description}</td>
                            <td class="px-4 py-3">{log.work_done}</td>
                            <td class="px-4 py-3">{log.technician}</td>
                            <td class="px-4 py-3 text-right">₹{log.cost}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>

