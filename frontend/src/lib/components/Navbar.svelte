<script>
    import { authStore } from '$lib/stores.js';
    import { goto } from '$app/navigation';

    let isMenuOpen = false;

    function logout() {
        authStore.logout();
        goto('/login');
    }
</script>

<nav class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
            <div class="flex items-center">
                <a href="/dashboard" class="flex items-center space-x-2">
                    <span class="text-2xl">🚲</span>
                    <span class="text-xl font-bold text-primary-700">VeloTrack</span>
                </a>

                {#if $authStore.isAuthenticated}
                    <div class="hidden md:flex ml-10 space-x-1">
                        <a href="/dashboard" class="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-primary-50 hover:text-primary-700">Dashboard</a>
                        <a href="/bicycles" class="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-primary-50 hover:text-primary-700">Bicycles</a>
                        <a href="/maintenance" class="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-primary-50 hover:text-primary-700">Maintenance</a>
                        <a href="/rentals" class="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-primary-50 hover:text-primary-700">Rentals</a>
                        <a href="/assistant" class="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-primary-50 hover:text-primary-700">🤖 Assistant</a>
                    </div>
                {/if}
            </div>

            <div class="flex items-center space-x-4">
                {#if $authStore.isAuthenticated}
                    <span class="text-sm text-gray-600 hidden sm:block">
                        {$authStore.user?.full_name || $authStore.user?.email}
                    </span>
                    <button on:click={logout} class="btn btn-outline text-sm">Logout</button>
                {:else}
                    <a href="/login" class="btn btn-primary text-sm">Login</a>
                {/if}

                <!-- Mobile menu button -->
                <button on:click={() => isMenuOpen = !isMenuOpen} class="md:hidden p-2">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>

    <!-- Mobile menu -->
    {#if isMenuOpen && $authStore.isAuthenticated}
        <div class="md:hidden border-t border-gray-200 bg-white">
            <div class="px-2 pt-2 pb-3 space-y-1">
                <a href="/dashboard" class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:bg-gray-50">Dashboard</a>
                <a href="/bicycles" class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:bg-gray-50">Bicycles</a>
                <a href="/maintenance" class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:bg-gray-50">Maintenance</a>
                <a href="/rentals" class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:bg-gray-50">Rentals</a>
                <a href="/assistant" class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:bg-gray-50">🤖 Assistant</a>
            </div>
        </div>
    {/if}
</nav>

