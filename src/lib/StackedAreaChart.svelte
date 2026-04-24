<script>
	import * as d3 from 'd3';
	import { rollingMean } from '$lib/utils.js';

	// rows: {dt, available, enroute, ontrip}[]
	// xDomain: [Date, Date] — shared domain so all charts align on identical pixel columns
	// gapRanges: [{start, end}] — date ranges to hide and exclude from smooth
	let { rows, xDomain = null, gapRanges = [], theme = 'dark' } = $props();

	const KEYS   = ['available', 'enroute', 'ontrip'];
	const COLORS = { available: '#EBA00F', enroute: '#007FA3', ontrip: '#6FC7EA' };
	const LABELS = { available: 'Available (searching)', enroute: 'En route (to pickup)', ontrip: 'On trip' };

	const THEMES = {
		dark: {
			bg:        '#181818',
			grid:      'rgba(255,255,255,0.11)',
			gridYear:  'rgba(255,255,255,0.07)',
			gridHov:   'rgba(255,255,255,0.28)',
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
			gapFill:   '#181818',
			edgeStroke:'white'
		},
		light: {
			bg:        '#f7f7f7',
			grid:      'rgba(0,0,0,0.10)',
			gridYear:  'rgba(0,0,0,0.06)',
			gridHov:   'rgba(0,0,0,0.25)',
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
			gapFill:   '#f7f7f7',
			edgeStroke:'rgba(255,255,255,0.6)'
		}
	};

	const T = $derived(THEMES[theme] ?? THEMES.dark);

	const GRID      = $derived(T.grid);
	const GRID_YEAR = $derived(T.gridYear);
	const GRID_HOV  = $derived(T.gridHov);
	const AXIS      = $derived(T.axis);
	const LABEL     = $derived(T.label);

	const margin = { top: 76, right: 112, bottom: 68, left: 80 };
	const W      = 1000;
	const H      = 488;
	const innerW = W - margin.left - margin.right;
	const innerH = H - margin.top - margin.bottom;

	let windowSize = $state(30);
	let hovered    = $state(null);
	let svgEl      = $state(null);

	const stackGen = d3.stack().keys(KEYS);

	function inGap(dt) {
		return gapRanges.some((r) => dt >= r.start && dt <= r.end);
	}

	function isGapRow(d) {
		return (d.available === 0 && d.enroute === 0 && d.ontrip === 0) || inGap(d.dt);
	}

	const smoothedRows = $derived(
		rows.length
			? (() => {
					// Pre-compute gap flags once to avoid repeated inGap scans.
					const isGap = rows.map((d) => isGapRow(d));

					// Rolling mean that excludes gap rows from the window so they don't
					// pull the smooth toward zero near the gap boundaries.
					const sm = (col) => {
						if (windowSize <= 1) return rows.map((d) => d[col]);
						const valid    = rows.filter((_, i) => !isGap[i]);
						const smoothed = rollingMean(valid.map((d) => d[col]), windowSize);
						const dtMap    = new Map(valid.map((d, i) => [d.dt.getTime(), smoothed[i]]));
						return rows.map((d, i) => (isGap[i] ? 0 : (dtMap.get(d.dt.getTime()) ?? 0)));
					};

					const av = sm('available'), en = sm('enroute'), on = sm('ontrip');
					return rows.map((d, i) => ({
						dt:        d.dt,
						isGap:     isGap[i],
						available: isGap[i] ? 0 : Math.max(0, av[i] || 0),
						enroute:   isGap[i] ? 0 : Math.max(0, en[i] || 0),
						ontrip:    isGap[i] ? 0 : Math.max(0, on[i] || 0)
					}));
				})()
			: []
	);

	const series = $derived(smoothedRows.length ? stackGen(smoothedRows) : []);

	// Use shared xDomain when provided so all charts align on identical pixel columns.
	const effectiveDomain = $derived(
		xDomain ?? (smoothedRows.length ? d3.extent(smoothedRows, (d) => d.dt) : null)
	);

	const xScale = $derived(
		effectiveDomain
			? d3.scaleTime().domain(effectiveDomain).range([0, innerW])
			: null
	);

	const yScale = $derived(
		series.length
			? d3.scaleLinear()
					.domain([0, d3.max(series[series.length - 1].filter((d) => !d.data.isGap), (d) => d[1]) * 1.05])
					.nice()
					.range([innerH, 0])
			: null
	);

	const areaPaths = $derived(
		xScale && yScale && series.length
			? series.map((s) =>
					d3
						.area()
						.x((d) => xScale(d.data.dt))
						.y0((d) => yScale(d[0]))
						.y1((d) => yScale(d[1]))
						.curve(d3.curveMonotoneX)
						.defined((d) => !d.data.isGap)(s)
				)
			: []
	);

	const edgePaths = $derived(
		xScale && yScale && series.length
			? series.map((s) =>
					d3
						.line()
						.x((d) => xScale(d.data.dt))
						.y((d) => yScale(d[1]))
						.curve(d3.curveMonotoneX)
						.defined((d) => !d.data.isGap)(s)
				)
			: []
	);

	const yTicks = $derived(yScale ? yScale.ticks(6) : []);

	const yTickFmt = (v) => {
		if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
		if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
		return `${v}`;
	};

	// All tick/label computations use effectiveDomain so every chart shares the same marks.
	const monthTicks = $derived(
		xScale && effectiveDomain
			? d3.timeMonths(effectiveDomain[0], effectiveDomain[1])
			: []
	);
	const yearTicks = $derived(
		xScale && effectiveDomain
			? d3.timeYears(effectiveDomain[0], effectiveDomain[1])
			: []
	);
	const yearLabels = $derived(
		xScale && effectiveDomain && yearTicks.length
			? (() => {
					const [s, e] = effectiveDomain;
					return yearTicks
						.map((y) => {
							const next = new Date(y.getFullYear() + 1, 0, 1);
							const mid  = new Date(((y < s ? s : y).getTime() + (next > e ? e : next).getTime()) / 2);
							return { year: y.getFullYear(), x: xScale(mid) };
						})
						.filter((l) => l.x >= 0 && l.x <= innerW);
				})()
			: []
	);

	// Gap overlay rects for each gap range.
	const gapRects = $derived(
		xScale && gapRanges.length
			? gapRanges.map((r) => {
					const x0 = xScale(r.start);
					const x1 = xScale(new Date(r.end.getTime() + 86400000));
					return { x: x0, w: Math.max(2, x1 - x0) };
				})
			: []
	);

	const bisect = d3.bisector((d) => d.dt).left;
	const dateFmt = d3.timeFormat('%b %d, %Y');
	const numFmt  = (v) => Math.round(v).toLocaleString('en-CA');

	function onMouseMove(e) {
		if (!xScale || !smoothedRows.length || !svgEl) return;
		const rect = svgEl.getBoundingClientRect();
		const mx   = (e.clientX - rect.left) * (W / rect.width) - margin.left;
		if (mx < 0 || mx > innerW) { hovered = null; return; }
		const date = xScale.invert(mx);
		const i    = bisect(smoothedRows, date);
		const d0   = smoothedRows[Math.max(0, i - 1)];
		const d1   = smoothedRows[Math.min(smoothedRows.length - 1, i)];
		const d    = (!d1 || Math.abs(date - d0.dt) <= Math.abs(date - d1.dt)) ? d0 : d1;
		if (d.isGap) { hovered = null; return; }
		hovered    = { dt: d.dt, available: d.available, enroute: d.enroute, ontrip: d.ontrip, x: xScale(d.dt) };
	}
</script>

<div class="chart-wrap">
	{#if !smoothedRows.length}
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

			<text x={margin.left} y={24} font-family="TradeGothicBold, sans-serif" font-size="21" fill={T.title}>Total kilomtres travelled by ridehailing vehicles per day</text>

			<!-- caption aligned to y-axis -->
			<text x={margin.left} y={H - 10} font-family="OpenSans, sans-serif" font-size="11" fill={T.caption}>Source: City of Toronto. Chart: Jeff Allen & Mia Wang</text>

			<g transform="translate({margin.left},{margin.top})">

				<!-- year vertical gridlines -->
				{#each yearTicks as tick}
					<line x1={xScale(tick)} x2={xScale(tick)} y1={0} y2={innerH} stroke={GRID_YEAR} stroke-width="1" />
				{/each}

				<!-- horizontal y gridlines -->
				{#each yTicks as tick}
					<line x1={0} x2={innerW} y1={yScale(tick)} y2={yScale(tick)} stroke={GRID} stroke-width="1" />
				{/each}

				<!-- stacked areas -->
				{#each areaPaths as path, i}
					<path d={path} fill={COLORS[KEYS[i]]} opacity="0.8" />
				{/each}

				<!-- thin white line at top of each phase — separates stacked layers clearly -->
				{#each edgePaths as path, i}
					<path d={path} fill="none" stroke={T.edgeStroke} stroke-width={windowSize === 1 ? 0.25 : 0.5} />
				{/each}

				<!-- gap overlays — rendered after areas so they clearly cover the gap region -->
				{#each gapRects as gr}
					<rect x={gr.x} y={0} width={gr.w} height={innerH}
						fill={T.gapFill} stroke="none" style="pointer-events: none" />
				{/each}

				<!-- hover vertical line -->
				{#if hovered}
					<line x1={hovered.x} x2={hovered.x} y1={0} y2={innerH} stroke={GRID_HOV} stroke-width="1" />
				{/if}

				<!-- legend — translate y=34 aligns swatches with tooltip swatches at by=7 -->
				<g transform="translate(10, 34)">
					{#each KEYS as key, i}
						<rect x={0} y={i * 19} width={11} height={11} fill={COLORS[key]} rx="2" opacity="0.85" />
						<text x={17} y={i * 19 + 9} font-family="OpenSans, sans-serif" font-size="11" fill={LABEL} dominant-baseline="middle">{LABELS[key]}</text>
					{/each}
				</g>

				<!-- x axis -->
				<line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke={AXIS} />
				{#each monthTicks as tick}
					<line x1={xScale(tick)} x2={xScale(tick)} y1={innerH} y2={innerH + 4}  stroke={AXIS} />
				{/each}
				{#each yearTicks as tick}
					<line x1={xScale(tick)} x2={xScale(tick)} y1={innerH} y2={innerH + 12} stroke={AXIS} stroke-width="1.5" />
				{/each}
				{#each yearLabels as lbl}
					<text x={lbl.x} y={innerH + 28} text-anchor="middle" font-family="OpenSans, sans-serif" font-size="13" fill={LABEL}>{lbl.year}</text>
				{/each}

				<!-- y axis -->
				<line x1={0} x2={0} y1={0} y2={innerH} stroke={AXIS} />
				{#each yTicks as tick}
					<g transform="translate(0,{yScale(tick)})">
						<line x2="-5" stroke={AXIS} />
						<text x="-10" text-anchor="end" dominant-baseline="middle" font-family="OpenSans, sans-serif" font-size="12" fill={LABEL}>{yTickFmt(tick)}</text>
					</g>
				{/each}

				<!-- tooltip: positioned at mid-2021; by=7 aligns swatches with legend (translate y=34) -->
				{#if hovered}
					{@const bx  = xScale(new Date(2021, 6, 1)) - 48}
					{@const by  = 7}
					{@const tot = hovered.available + hovered.enroute + hovered.ontrip}
					<rect x={bx} y={by} width={230} height={110} rx="4" fill={T.tooltipBg} stroke={T.tooltipBd} stroke-width="1" />
					<text x={bx+12} y={by+19} font-family="OpenSans, sans-serif" font-size="11" fill={T.tooltipDt}>{dateFmt(hovered.dt)}</text>
					{#each KEYS as key, i}
						{@const pct = tot > 0 ? Math.round(hovered[key] / tot * 100) : 0}
						<rect  x={bx+12} y={by + 28 + i * 19} width={9} height={9} fill={COLORS[key]} rx="1" opacity="0.85" />
						<text  x={bx+26} y={by + 36 + i * 19} font-family="OpenSans, sans-serif" font-size="11" fill={T.tooltipRow} dominant-baseline="middle">
							{numFmt(hovered[key])} km ({pct}%)
						</text>
					{/each}
					<!-- divider -->
					<line x1={bx+12} x2={bx+218} y1={by+87} y2={by+87} stroke={T.tooltipDiv} stroke-width="1" />
					<text x={bx+12} y={by+101} font-family="OpenSansBold, sans-serif" font-size="11" fill={T.tooltipTot}>Total: {numFmt(tot)} km</text>
				{/if}

				<!-- invisible interaction overlay -->
				<rect role="presentation" x={0} y={0} width={innerW} height={innerH} fill="transparent" style="cursor: crosshair"
					onmousemove={onMouseMove} onmouseleave={() => (hovered = null)} />

			</g>

			<!-- Daily / 30-day average toggle buttons, positioned in the subtitle zone -->
			<rect x={margin.left} y={38} width={58} height={20} rx="3"
				fill={windowSize === 1 ? (theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.10)') : 'transparent'}
				stroke={theme === 'dark' ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.20)'} stroke-width="1"
				style="cursor: pointer"
				role="button"
				tabindex="0"
				onclick={() => (windowSize = 1)}
				onkeydown={(e) => e.key === 'Enter' && (windowSize = 1)} />
			<text x={margin.left + 29} y={51} text-anchor="middle"
				font-family="OpenSans, sans-serif" font-size="11"
				fill={windowSize === 1 ? T.title : T.label}
				style="pointer-events: none">Daily</text>

			<rect x={margin.left + 62} y={38} width={112} height={20} rx="3"
				fill={windowSize === 30 ? (theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.10)') : 'transparent'}
				stroke={theme === 'dark' ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.20)'} stroke-width="1"
				style="cursor: pointer"
				role="button"
				tabindex="0"
				onclick={() => (windowSize = 30)}
				onkeydown={(e) => e.key === 'Enter' && (windowSize = 30)} />
			<text x={margin.left + 118} y={51} text-anchor="middle"
				font-family="OpenSans, sans-serif" font-size="11"
				fill={windowSize === 30 ? T.title : T.label}
				style="pointer-events: none">30-day average</text>

		</svg>
	{/if}
</div>

<style>
	.chart-wrap {
		max-width: 1060px;
		margin: 0 auto;
		padding: 0 20px;
		position: relative;
	}
	.loading {
		text-align: center;
		color: #555;
		padding-top: 60px;
	}
</style>
