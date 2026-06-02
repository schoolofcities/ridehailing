<script>
	import * as d3 from 'd3';

	// rows: {hr: string, time_ontrip, time_enroute, time_available}[]  (minutes)
	let { rows, theme = 'dark' } = $props();

	const KEYS   = ['time_available', 'time_enroute', 'time_waiting', 'time_ontrip'];
	const COLORS = { time_available: '#EBA00F', time_waiting: '#C05F2C', time_enroute: '#007FA3', time_ontrip: '#6FC7EA' };
	const LABELS = { time_available: 'Available (searching)', time_waiting: 'Waiting at pickup', time_enroute: 'En route (to pickup)', time_ontrip: 'On trip' };

	const THEMES = {
		dark: {
			bg:        '#181818',
			grid:      'rgba(255,255,255,0.11)',
			axis:      'rgba(255,255,255,0.32)',
			label:     '#aaa',
			title:     '#f0f0f0',
			caption:   '#555',
			tooltipBg: '#222',
			tooltipBd: 'rgba(255,255,255,0.22)',
			tooltipDt: '#999',
			tooltipRow:'#ccc',
			tooltipTot:'#eee',
			tooltipDiv:'rgba(255,255,255,0.1)',
			edgeStroke:'white', legendStroke:'black',
		},
		light: {
			bg:        '#f7f7f7',
			grid:      'rgba(0,0,0,0.10)',
			axis:      'rgba(0,0,0,0.30)',
			label:     '#666',
			title:     '#111',
			caption:   '#aaa',
			tooltipBg: '#ececec',
			tooltipBd: 'rgba(0,0,0,0.18)',
			tooltipDt: '#777',
			tooltipRow:'#333',
			tooltipTot:'#111',
			tooltipDiv:'rgba(0,0,0,0.12)',
			edgeStroke:'rgba(255,255,255,0.6)', legendStroke:'rgba(0,0,0,0.5)',
		}
	};

	const T = $derived(THEMES[theme] ?? THEMES.dark);

	const margin = { top: 96, right: 180, bottom: 68, left: 80 };
	const W      = 1000;
	const H      = 420;
	const innerW = W - margin.left - margin.right;
	const innerH = H - margin.top - margin.bottom;

	let hovered  = $state(null);
	let svgEl    = $state(null);
	let showPct  = $state(false);

	const stackGen    = d3.stack().keys(KEYS);
	const stackGenPct = d3.stack().keys(KEYS).offset(d3.stackOffsetExpand);

	const stackRows = $derived(
		rows.map((d) => ({
			hr:             d.hr,
			time_available: d.time_available,
			time_waiting:   d.time_waiting,
			time_enroute:   d.time_enroute,
			time_ontrip:    d.time_ontrip,
		}))
	);

	const series = $derived(
		stackRows.length ? (showPct ? stackGenPct(stackRows) : stackGen(stackRows)) : []
	);

	const xScale = $derived(
		stackRows.length
			? d3.scaleBand()
					.domain(stackRows.map((d) => d.hr))
					.range([0, innerW])
					.padding(0.18)
			: null
	);

	const yScale = $derived(
		series.length
			? d3.scaleLinear()
					.domain(showPct ? [0, 1] : [0, d3.max(series[series.length - 1], (d) => d[1]) * 1.05])
					.nice()
					.range([innerH, 0])
			: null
	);

	const yTicks = $derived(yScale ? yScale.ticks(6) : []);

	const yTickFmt = (v) => {
		if (showPct) return `${Math.round(v * 100)}%`;
		if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
		if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
		if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
		return `${v}`;
	};

	// Format minutes for tooltip
	const timeFmt = (mins) => {
		if (mins >= 1e6) return `${(mins / 1e6).toFixed(2)}M min`;
		if (mins >= 1e3) return `${(mins / 1e3).toFixed(0)}K min`;
		return `${Math.round(mins)} min`;
	};

	function onMouseMove(e) {
		if (!xScale || !stackRows.length || !svgEl) return;
		const rect = svgEl.getBoundingClientRect();
		const mx   = (e.clientX - rect.left) * (W / rect.width) - margin.left;
		if (mx < 0 || mx > innerW) { hovered = null; return; }
		const idx = Math.floor(mx / xScale.step());
		const d   = stackRows[Math.max(0, Math.min(stackRows.length - 1, idx))];
		hovered = { ...d, x: xScale(d.hr) + xScale.bandwidth() / 2 };
	}

	function btnFill(active) {
		return active
			? (theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.10)')
			: 'transparent';
	}
	function btnStroke() {
		return theme === 'dark' ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.20)';
	}
</script>

<div class="chart-wrap">
	{#if !stackRows.length}
		<p class="loading">Loading…</p>
	{:else}
		<svg
			bind:this={svgEl}
			width="100%"
			viewBox="0 0 {W} {H}"
			preserveAspectRatio="xMidYMid meet"
			style="cursor: default; display: block; width: 100%;"
		>
			<rect width={W} height={H} fill={T.bg} rx="6" />

			<text x={margin.left} y={24} font-family="TradeGothicBold, sans-serif" font-size="21" fill={T.title}>Total time on app by hour of day (2025)</text>
			<text x={margin.left} y={44} font-family="OpenSans, sans-serif" font-size="12" fill={T.label}>Total driver-minutes by vehicle phase for each hour of the day, summed across all of 2025.</text>

			<text x={margin.left} y={H - 10} font-family="OpenSans, sans-serif" font-size="10" fill={T.caption}>Source: City of Toronto. Chart: Jeff Allen & Mia Wang</text>

			<!-- Total / Percent toggle -->
			<rect x={margin.left} y={60} width={52} height={20} rx="3"
				fill={btnFill(!showPct)} stroke={btnStroke()} stroke-width="1"
				style="cursor: pointer" role="button" tabindex="0"
				onclick={() => (showPct = false)}
				onkeydown={(e) => e.key === 'Enter' && (showPct = false)} />
			<text x={margin.left + 26} y={73} text-anchor="middle"
				font-family="OpenSans, sans-serif" font-size="11"
				fill={!showPct ? T.title : T.label}
				style="pointer-events: none">Total</text>

			<rect x={margin.left + 56} y={60} width={64} height={20} rx="3"
				fill={btnFill(showPct)} stroke={btnStroke()} stroke-width="1"
				style="cursor: pointer" role="button" tabindex="0"
				onclick={() => (showPct = true)}
				onkeydown={(e) => e.key === 'Enter' && (showPct = true)} />
			<text x={margin.left + 88} y={73} text-anchor="middle"
				font-family="OpenSans, sans-serif" font-size="11"
				fill={showPct ? T.title : T.label}
				style="pointer-events: none">Percent</text>

			<g transform="translate({margin.left},{margin.top})">

				<!-- horizontal gridlines -->
				{#each yTicks as tick}
					<line x1={0} x2={innerW} y1={yScale(tick)} y2={yScale(tick)} stroke={T.grid} stroke-width="1" />
				{/each}

				<!-- stacked bars -->
				{#each series as s, si}
					{#each s as seg, i}
						<rect
							x={xScale(stackRows[i].hr)}
							y={yScale(seg[1])}
							width={xScale.bandwidth()}
							height={Math.max(0, yScale(seg[0]) - yScale(seg[1]))}
							fill={COLORS[KEYS[si]]}
							opacity={hovered && hovered.hr !== stackRows[i].hr ? 0.4 : 0.85}
						/>
					{/each}
				{/each}

				<!-- legend -->
				<g transform="translate({innerW + 12}, 0)">
					{#each [...KEYS].reverse() as key, i}
						<rect x={0.5} y={i * 19 + 0.5} width={10} height={10} fill={COLORS[key]} rx="2" opacity="0.85" stroke={T.legendStroke} stroke-width="1" />
						<text x={17} y={i * 19 + 9} font-family="OpenSans, sans-serif" font-size="11" fill={T.label} dominant-baseline="middle">{LABELS[key]}</text>
					{/each}
				</g>

				<!-- x axis -->
				<line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke={T.axis} />
				{#each stackRows as d}
					{@const hr = parseInt(d.hr)}
					{@const x  = xScale(d.hr)}
					<line x1={x} x2={x} y1={innerH} y2={innerH + 5} stroke={T.axis} />
					<text x={x} y={innerH + 18} text-anchor="middle" font-family="OpenSans, sans-serif" font-size="11" fill={T.label}>{hr}</text>
				{/each}
				<line
					x1={xScale(stackRows[stackRows.length - 1].hr) + xScale.bandwidth()}
					x2={xScale(stackRows[stackRows.length - 1].hr) + xScale.bandwidth()}
					y1={innerH} y2={innerH + 5} stroke={T.axis} />
				<text
					x={xScale(stackRows[stackRows.length - 1].hr) + xScale.bandwidth()}
					y={innerH + 18} text-anchor="middle" font-family="OpenSans, sans-serif" font-size="11" fill={T.label}>24</text>
				<text x={innerW / 2} y={innerH + 44} text-anchor="middle" font-family="OpenSans, sans-serif" font-size="12" fill={T.label}>Hour of day</text>

				<!-- y axis -->
				<line x1={0} x2={0} y1={0} y2={innerH} stroke={T.axis} />
				{#each yTicks as tick}
					<g transform="translate(0,{yScale(tick)})">
						<line x2="-5" stroke={T.axis} />
						<text x="-10" text-anchor="end" dominant-baseline="middle" font-family="OpenSans, sans-serif" font-size="12" fill={T.label}>{yTickFmt(tick)}</text>
					</g>
				{/each}

				<!-- tooltip -->
				{#if hovered}
					{@const bx  = hovered.x > innerW * 0.6 ? hovered.x - 250 : hovered.x + 14}
					{@const by  = 0}
					{@const tot = hovered.time_available + hovered.time_waiting + hovered.time_enroute + hovered.time_ontrip}
					<rect x={bx} y={by} width={230} height={129} rx="4" fill={T.tooltipBg} stroke={T.tooltipBd} stroke-width="1" />
					<text x={bx+12} y={by+19} font-family="OpenSans, sans-serif" font-size="11" fill={T.tooltipDt}>Hour {hovered.hr}</text>
					{#each [...KEYS].reverse() as key, i}
						{@const pct = tot > 0 ? Math.round(hovered[key] / tot * 100) : 0}
						<rect  x={bx+12} y={by + 28 + i * 19} width={9} height={9} fill={COLORS[key]} rx="1" opacity="0.85" />
						<text  x={bx+26} y={by + 36 + i * 19} font-family="OpenSans, sans-serif" font-size="11" fill={T.tooltipRow} dominant-baseline="middle">
							{timeFmt(hovered[key])} ({pct}%)
						</text>
					{/each}
					<line x1={bx+12} x2={bx+218} y1={by+106} y2={by+106} stroke={T.tooltipDiv} stroke-width="1" />
					<text x={bx+12} y={by+120} font-family="OpenSansBold, sans-serif" font-size="11" fill={T.tooltipTot}>Total: {timeFmt(tot)}</text>
				{/if}

				<!-- invisible interaction overlay -->
				<rect role="presentation" x={0} y={0} width={innerW} height={innerH} fill="transparent" style="cursor: crosshair"
					onmousemove={onMouseMove} onmouseleave={() => (hovered = null)} />

			</g>
		</svg>
	{/if}
</div>

<style>
	.chart-wrap {
		width: 100%;
		position: relative;
	}
	.loading {
		text-align: center;
		color: #555;
		padding-top: 60px;
	}
</style>
