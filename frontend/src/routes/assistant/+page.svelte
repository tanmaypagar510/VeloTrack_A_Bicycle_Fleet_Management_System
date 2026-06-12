<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { authStore, notifications } from '$lib/stores.js';
    import { assistantApi, bicyclesApi } from '$lib/api.js';

    let question = '';
    let messages = [];
    let bicycles = [];
    let selectedBikeId = null;
    let loading = false;
    let chatLoading = false;

    onMount(async () => {
        if (!$authStore.isAuthenticated) { goto('/login'); return; }

        // Check URL params for pre-scoped bike
        const urlBikeId = $page.url.searchParams.get('bike_id');
        if (urlBikeId) selectedBikeId = parseInt(urlBikeId);

        try {
            const res = await bicyclesApi.getAll();
            bicycles = res.bicycles || [];
        } catch (e) {}

        // Load chat history
        try {
            const res = await assistantApi.getHistory();
            if (res.history) {
                messages = res.history.reverse().map(h => ({
                    type: 'exchange',
                    question: h.question,
                    answer: h.answer,
                    context: h.context_used,
                    bike_id: h.bicycle_id
                }));
            }
        } catch (e) {}
    });

    async function askQuestion() {
        if (!question.trim()) return;

        const q = question;
        question = '';
        chatLoading = true;

        messages = [...messages, { type: 'exchange', question: q, answer: null, context: null, bike_id: selectedBikeId }];

        try {
            const res = await assistantApi.ask(q, selectedBikeId);
            messages = messages.map((m, i) =>
                i === messages.length - 1
                    ? { ...m, answer: res.answer, context: res.context_used }
                    : m
            );
        } catch (err) {
            messages = messages.map((m, i) =>
                i === messages.length - 1
                    ? { ...m, answer: 'Sorry, I encountered an error. Please try again.' }
                    : m
            );
            notifications.add('Failed to get response', 'error');
        } finally {
            chatLoading = false;
        }

        // Scroll to bottom
        setTimeout(() => {
            const el = document.getElementById('chat-container');
            if (el) el.scrollTop = el.scrollHeight;
        }, 100);
    }

    function getBikeName(bikeId) {
        const bike = bicycles.find(b => b.id === bikeId);
        return bike ? `${bike.bike_code} (${bike.make} ${bike.model})` : `Bike #${bikeId}`;
    }
</script>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-800">🤖 Maintenance Assistant</h1>
        <p class="text-gray-500">AI-powered fleet maintenance recommendations</p>
    </div>

    <!-- Bike Selector -->
    <div class="card mb-4">
        <div class="flex items-center gap-4">
            <label class="text-sm font-medium text-gray-700 whitespace-nowrap">Scope to bike:</label>
            <select bind:value={selectedBikeId} class="input max-w-xs">
                <option value={null}>All bikes (fleet-wide)</option>
                {#each bicycles as bike}
                    <option value={bike.id}>{bike.bike_code} - {bike.make} {bike.model}</option>
                {/each}
            </select>
            {#if selectedBikeId}
                <a href="/bicycles/{selectedBikeId}" class="text-primary-600 text-sm hover:underline">View bike →</a>
            {/if}
        </div>
    </div>

    <!-- Chat Container -->
    <div class="card mb-4" style="height: 500px; display: flex; flex-direction: column;">
        <div id="chat-container" class="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
            {#if messages.length === 0}
                <div class="text-center text-gray-400 py-16">
                    <p class="text-4xl mb-4">🤖</p>
                    <p class="text-lg mb-2">Ask me anything about your fleet!</p>
                    <div class="text-sm space-y-1">
                        <p class="text-gray-400">Try asking:</p>
                        <p class="italic">"Which bikes haven't been serviced in the last 30 days?"</p>
                        <p class="italic">"What problems has bike #42 had in the past?"</p>
                        <p class="italic">"Does bike #15 need maintenance soon?"</p>
                        <p class="italic">"What was the most common issue last month?"</p>
                    </div>
                </div>
            {:else}
                {#each messages as msg, i}
                    <!-- User Question -->
                    <div class="flex justify-end">
                        <div class="bg-primary-600 text-white rounded-2xl rounded-tr-md px-4 py-2 max-w-[80%]">
                            <p class="text-sm">{msg.question}</p>
                            {#if msg.bike_id}
                                <p class="text-xs opacity-75 mt-1">📍 About: {getBikeName(msg.bike_id)}</p>
                            {/if}
                        </div>
                    </div>

                    <!-- Assistant Response -->
                    <div class="flex justify-start">
                        <div class="bg-gray-100 rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%]">
                            {#if msg.answer}
                                <p class="text-sm whitespace-pre-wrap">{msg.answer}</p>

                                {#if msg.context && msg.context.length > 0}
                                    <details class="mt-3">
                                        <summary class="text-xs text-primary-600 cursor-pointer hover:underline">
                                            📄 View source records ({msg.context.length})
                                        </summary>
                                        <div class="mt-2 space-y-1">
                                            {#each msg.context as ctx}
                                                <div class="text-xs bg-white rounded p-2 border border-gray-200">
                                                    {ctx.text}
                                                </div>
                                            {/each}
                                        </div>
                                    </details>
                                {/if}
                            {:else}
                                <div class="flex items-center gap-2">
                                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                                    <span class="text-sm text-gray-500">Thinking...</span>
                                </div>
                            {/if}
                        </div>
                    </div>
                {/each}
            {/if}
        </div>

        <!-- Input -->
        <form on:submit|preventDefault={askQuestion} class="flex gap-2 border-t pt-3">
            <input
                bind:value={question}
                class="input flex-1"
                placeholder="Ask about maintenance, rentals, or bike conditions..."
                disabled={chatLoading}
            />
            <button type="submit" class="btn btn-primary" disabled={chatLoading || !question.trim()}>
                {chatLoading ? '...' : 'Send'}
            </button>
        </form>
    </div>
</div>

