<script>
    export let score = 0;
    export let level = 'Low';
    export let showTooltip = false;
    export let featureImportance = [];

    let tooltipOpen = false;

    $: badgeClass = level === 'High' ? 'badge-red' : level === 'Medium' ? 'badge-yellow' : 'badge-green';

    function toggleTooltip() {
        if (showTooltip) {
            tooltipOpen = !tooltipOpen;
        }
    }
</script>

<div class="relative inline-block">
    <button
        class="badge {badgeClass} cursor-pointer hover:opacity-80"
        on:click={toggleTooltip}
        title={showTooltip ? 'Click for details' : `Risk: ${score}`}
    >
        {level} ({score})
    </button>

    {#if tooltipOpen && featureImportance?.length > 0}
        <div class="absolute z-50 w-64 p-3 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 left-0 top-full">
            <div class="flex justify-between items-center mb-2">
                <h4 class="text-xs font-semibold text-gray-600 uppercase">Why this score?</h4>
                <button on:click={() => tooltipOpen = false} class="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <ul class="space-y-1">
                {#each featureImportance as item}
                    <li class="text-sm text-gray-700 flex items-start">
                        <span class="text-primary-500 mr-1.5 mt-0.5">•</span>
                        <span>{item.feature}</span>
                    </li>
                {/each}
            </ul>
        </div>
    {/if}
</div>

