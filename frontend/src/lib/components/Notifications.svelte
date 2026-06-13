<script>
    import { notifications } from '$lib/stores.js';
</script>

<div class="fixed top-20 right-4 z-50 space-y-2 max-w-sm">
    {#each $notifications as notification (notification.id)}
        <div
            class="rounded-lg p-4 shadow-lg border transition-all duration-300 {
                notification.type === 'success' ? 'bg-green-50 border-green-200 text-green-800' :
                notification.type === 'error' ? 'bg-red-50 border-red-200 text-red-800' :
                notification.type === 'warning' ? 'bg-yellow-50 border-yellow-200 text-yellow-800' :
                'bg-blue-50 border-blue-200 text-blue-800'
            }"
        >
            <div class="flex justify-between items-start">
                <p class="text-sm">{notification.message}</p>
                <button
                    on:click={() => notifications.remove(notification.id)}
                    class="ml-2 text-gray-400 hover:text-gray-600"
                >✕</button>
            </div>
        </div>
    {/each}
</div>

