<script>
    import '../app.css';
    import Navbar from '$lib/components/Navbar.svelte';
    import Notifications from '$lib/components/Notifications.svelte';
</script>

<div class="min-h-screen bg-gray-50">
    <Navbar />
    <Notifications />
    <main>
        <slot />
    </main>
</div>

