<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { authStore, notifications } from '$lib/stores.js';
    import { rentalsApi, bicyclesApi } from '$lib/api.js';

    let rentals = [];
    let bicycles = [];
    let loading = true;
    let showCheckoutForm = false;
    let statusFilter = '';

    let checkout = { bicycle_id: '', renter_name: '', renter_contact: '', notes: '', rate_per_hour: 50 };

    onMount(async () => {
        if (!$authStore.isAuthenticated) { goto('/login'); return; }
        await loadData();
    });

    async function loadData() {
        loading = true;
        try {
            const [rentalsRes, bikesRes] = await Promise.all([
                rentalsApi.getAll(),
                bicyclesApi.getAll()
            ]);
            rentals = rentalsRes.rentals || [];
            bicycles = bikesRes.bicycles || [];
        } catch (err) {
            notifications.add('Failed to load rentals', 'error');
        } finally {
            loading = false;
        }
    }

    $: availableBikes = bicycles.filter(b => b.status === 'Available');
    $: filteredRentals = statusFilter ? rentals.filter(r => r.status === statusFilter) : rentals;

    async function handleCheckout() {
        try {
            await rentalsApi.checkout({
                bicycle_id: parseInt(checkout.bicycle_id),
                renter_name: checkout.renter_name,
                renter_contact: checkout.renter_contact,
                notes: checkout.notes,
                rate_per_hour: parseFloat(checkout.rate_per_hour) || 50
            });
            notifications.add('Bicycle checked out successfully!', 'success');
            showCheckoutForm = false;
            checkout = { bicycle_id: '', renter_name: '', renter_contact: '', notes: '', rate_per_hour: 50 };
            await loadData();
        } catch (err) {
            notifications.add(err.message || 'Checkout failed', 'error');
        }
    }

    async function handleReturn(rentalId) {
        try {
            await rentalsApi.return(rentalId);
            notifications.add('Bicycle returned successfully!', 'success');
            await loadData();
        } catch (err) {
            notifications.add(err.message || 'Return failed', 'error');
        }
    }

    function getBikeName(bikeId) {
        const bike = bicycles.find(b => b.id === bikeId);
        return bike ? bike.bike_code : `#${bikeId}`;
    }
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex justify-between items-center mb-6">
        <div>
            <h1 class="text-3xl font-bold text-gray-800">Rentals</h1>
            <p class="text-gray-500">Check-in and check-out bicycles</p>
        </div>
        <button on:click={() => showCheckoutForm = !showCheckoutForm} class="btn btn-primary">
            {showCheckoutForm ? 'Cancel' : '🔑 New Checkout'}
        </button>
    </div>

    {#if showCheckoutForm}
        <div class="card mb-6">
            <h3 class="text-lg font-semibold mb-4">Checkout Bicycle</h3>
            <form on:submit|preventDefault={handleCheckout} class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Bicycle *</label>
                    <select bind:value={checkout.bicycle_id} class="input" required>
                        <option value="">Select available bicycle</option>
                        {#each availableBikes as bike}
                            <option value={bike.id}>{bike.bike_code} - {bike.make} {bike.model}</option>
                        {/each}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Renter Name *</label>
                    <input bind:value={checkout.renter_name} class="input" placeholder="Jane Doe" required />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Contact</label>
                    <input bind:value={checkout.renter_contact} class="input" placeholder="+91 9876543210" />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Rate (₹/hour)</label>
                    <input bind:value={checkout.rate_per_hour} class="input" type="number" min="10" step="5" />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                    <input bind:value={checkout.notes} class="input" placeholder="Any special notes..." />
                </div>
                <div class="md:col-span-2">
                    <button type="submit" class="btn btn-success">Checkout Bicycle</button>
                </div>
            </form>
        </div>
    {/if}

    <!-- Filter -->
    <div class="mb-4">
        <select bind:value={statusFilter} class="input max-w-xs">
            <option value="">All Rentals</option>
            <option value="Active">Active</option>
            <option value="Returned">Returned</option>
        </select>
    </div>

    {#if loading}
        <div class="flex justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
    {:else if filteredRentals.length === 0}
        <div class="text-center py-20 text-gray-400">
            <p class="text-4xl mb-4">🔑</p>
            <p>No rentals found</p>
        </div>
    {:else}
        <div class="card overflow-x-auto">
            <table class="w-full text-sm">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left">Bicycle</th>
                        <th class="px-4 py-3 text-left">Renter</th>
                        <th class="px-4 py-3 text-left">Checkout (IST)</th>
                        <th class="px-4 py-3 text-left">Return (IST)</th>
                        <th class="px-4 py-3 text-left">Duration</th>
                        <th class="px-4 py-3 text-right">Cost (₹)</th>
                        <th class="px-4 py-3 text-left">Status</th>
                        <th class="px-4 py-3 text-left">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {#each filteredRentals as rental}
                        <tr class="border-t hover:bg-gray-50 {rental.is_anomalous ? 'bg-red-50' : ''}">
                            <td class="px-4 py-3 font-medium">{getBikeName(rental.bicycle_id)}</td>
                            <td class="px-4 py-3">{rental.renter_name}</td>
                            <td class="px-4 py-3">{new Date(rental.checkout_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})}</td>
                            <td class="px-4 py-3">{rental.return_time ? new Date(rental.return_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) : '—'}</td>
                            <td class="px-4 py-3">{rental.duration_hours ? rental.duration_hours + 'h' : '—'}</td>
                            <td class="px-4 py-3 text-right">{rental.rental_cost ? '₹' + rental.rental_cost : '—'}</td>
                            <td class="px-4 py-3">
                                <span class="badge {rental.status === 'Active' ? 'badge-blue' : 'badge-green'}">{rental.status}</span>
                                {#if rental.is_anomalous}<span class="badge badge-red ml-1" title={rental.anomaly_reason}>⚠ Anomaly</span>{/if}
                            </td>
                            <td class="px-4 py-3">
                                {#if rental.status === 'Active'}
                                    <button on:click={() => handleReturn(rental.id)} class="btn btn-success text-xs">Return</button>
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>

