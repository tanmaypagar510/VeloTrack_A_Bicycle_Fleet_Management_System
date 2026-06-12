<script>
    export let data = [];
    export let width = 120;
    export let height = 30;

    $: points = (() => {
        if (!data || data.length < 2) return '';
        const maxVal = Math.max(...data.map(d => d.score || 0), 1);
        const minVal = Math.min(...data.map(d => d.score || 0), 0);
        const range = maxVal - minVal || 1;
        const stepX = width / (data.length - 1);

        return data.map((d, i) => {
            const x = i * stepX;
            const y = height - ((d.score - minVal) / range) * (height - 4) - 2;
            return `${x},${y}`;
        }).join(' ');
    })();

    $: color = data.length > 0 && data[data.length - 1]?.score > 66 ? '#ef4444' : data.length > 0 && data[data.length - 1]?.score > 33 ? '#f59e0b' : '#22c55e';
</script>

<svg {width} {height} class="inline-block">
    {#if points}
        <polyline
            fill="none"
            stroke={color}
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            points={points}
        />
    {:else}
        <text x="50%" y="50%" text-anchor="middle" dy="0.3em" class="text-xs fill-gray-400">No data</text>
    {/if}
</svg>

