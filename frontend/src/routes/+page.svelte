<script>
    import { authStore } from '$lib/stores.js';
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';

    onMount(() => {
        if ($authStore.isAuthenticated) {
            goto('/dashboard');
        }
    });
</script>

<div class="flex items-center justify-center min-h-[80vh]">
    <div class="text-center max-w-2xl px-4">
        <div class="text-6xl mb-4">🚲</div>
        <h1 class="text-4xl font-bold text-primary-700 mb-4">VeloTrack</h1>
        <p class="text-xl text-gray-600 mb-8">Bicycle Fleet Management System</p>
        <p class="text-gray-500 mb-8">
            Cloud-native fleet management for bicycle rental businesses.
            Track bicycles, manage maintenance, monitor rentals, and get AI-powered maintenance predictions.
        </p>
        <div class="flex justify-center space-x-4">
            <a href="/login" class="btn btn-primary text-lg px-8 py-3">Login</a>
            <a href="/register" class="btn btn-outline text-lg px-8 py-3">Register</a>
        </div>
    </div>
</div>

