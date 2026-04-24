<script>
	import * as d3 from 'd3';

	// rows: {dt, value}[]   smooth: {dt, value}[]
	// xDomain: [Date, Date] — shared domain so all charts share the same x-axis scale
	// gapRanges: [{start: Date, end: Date}] — date ranges to visually mark and exclude from hover
	// colourMode: 'flat' (default) | 'gradient' (y-value based red→yellow→blue)
	let {
		rows,
		smooth,
		title,
		subtitle,
		darkColour  = '#F1C500',
		lightColour = '#D4A900',
		colourMode  = 'flat',
		yTickFmt    = (v) => v.toLocaleString(),
		tooltipFmt  = (v) => v.toLocaleString(),
		xDomain     = null,
		gapRanges   = [],
		theme       = 'dark'
	} = $props();

	const THEMES = {
		dark: {
			bg:        '#181818',
			grid:      'rgba(255,255,255,0.11)',
			gridYear:  'rgba(255,255,255,0.07)',
			gridHov:   'rgba(255,255,255,0.28)',
			axis:      'rgba(255,255,255,0.32)',
			label:     '#aaa',
			title:     '#f0f0f0',
			subtitle:  '#c0c0c0',
			caption:   '#555',
			tooltipBg: '#222',
			tooltipBd: 'rgba(255,255,255,0.22)',
			tooltipDt: '#999',
			tooltipVal:'#eee',
			gapFill:   '#181818'
		},
		light: {
			bg:        '#f7f7f7',
			grid:      'rgba(0,0,0,0.10)',
			gridYear:  'rgba(0,0,0,0.06)',
			gridHov:   'rgba(0,0,0,0.25)',
			axis:      'rgba(0,0,0,0.30)',
			label:     '#666',
			title:     '#111',
			subtitle:  '#444',
			caption:   '#aaa',
			tooltipBg: '#ececec',
			tooltipBd: 'rgba(0,0,0,0.18)',
			tooltipDt: '#777',
			tooltipVal:'#111',
			gapFill:   '#f7f7f7'
		}
	};

	const T = $derived(THEMES[theme] ?? THEMES.dark);

	// Active colour switches with theme
	const colour = $derived(theme === 'light' ? lightColour : darkColour);

	const GRID      = $derived(T.grid);
	const GRID_YEAR = $derived(T.gridYear);
	const GRID_HOV  = $derived(T.gridHov);
	const AXIS      = $derived(T.axis);
	const LABEL     = $derived(T.label);

	const margin = { top: 76, right: 112, bottom: 68, left: 80 };
	const W      = 1000;
	const H      = 488; // extra 8px for in-SVG caption
	const innerW = W - margin.left - margin.right;
	const innerH = H - margin.top - margin.bottom;

	// unique ID so multiple gradient instances don't clash
	const uid = Math.random().toString(36).slice(2, 7);

	let hovered = $state(null);
	let svgEl   = $state(null);

	// Use shared xDomain when provided so all charts align on identical pixel columns.
	const effectiveDomain = $derived(
		xDomain ?? (rows.length ? d3.extent(rows, (d) => d.dt) : null)
	);

	const xScale = $derived(
		effectiveDomain
			? d3.scaleTime().domain(effectiveDomain).range([0, innerW])
			: null
	);

	const yScale = $derived(
		rows.length
			? d3.scaleLinear()
					.domain([0, d3.max(rows.filter((d) => d.value !== null), (d) => d.value) * 1.05])
					.nice()
					.range([innerH, 0])
			: null
	);

	// Per-dot colour scale for gradient mode
	const dotColourScale = $derived(
		colourMode === 'gradient' && rows.length
			? (() => {
					const [lo, hi] = d3.extent(rows.filter(d => d.value !== null), (d) => d.value);
					return d3.scaleLinear()
						.domain([lo, (lo + hi) / 2, hi])
						.range(['#DC4633', '#F1C500', '#007FA3'])
						.interpolate(d3.interpolateRgb);
				})()
			: null
	);

	const smoothPath = $derived(
		xScale && yScale
			? d3.line()
					.x((d) => xScale(d.dt))
					.y((d) => yScale(d.value))
					.curve(d3.curveMonotoneX)
					.defined((d) => d.value !== null && !isNaN(d.value))(smooth)
			: ''
	);

	const lineLabel = $derived(
		smooth.length && xScale && yScale
			? (() => {
					const last = [...smooth].reverse().find((d) => !isNaN(d.value) && d.value !== null);
					return last ? { x: xScale(last.dt) + 8, y: yScale(last.value) } : null;
				})()
			: null
	);

	const yTicks = $derived(yScale ? yScale.ticks(6) : []);

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

	// Pre-compute gap overlay rects (x, width) for each gap range.
	const gapRects = $derived(
		xScale && gapRanges.length
			? gapRanges.map((r) => {
					const x0 = xScale(r.start);
					// +1 day so the end day is fully covered
					const x1 = xScale(new Date(r.end.getTime() + 86400000));
					return { x: x0, w: Math.max(2, x1 - x0) };
				})
			: []
	);

	const bisect = d3.bisector((d) => d.dt).left;
	const dateFmt = d3.timeFormat('%b %d, %Y');

	function inGap(dt) {
		return gapRanges.some((r) => dt >= r.start && dt <= r.end);
	}

	function onMouseMove(e) {
		if (!xScale || !rows.length || !svgEl) return;
		const rect = svgEl.getBoundingClientRect();
		const mx   = (e.clientX - rect.left) * (W / rect.width) - margin.left;
		if (mx < 0 || mx > innerW) { hovered = null; return; }
		const date = xScale.invert(mx);
		const i    = bisect(rows, date);
		const d0   = rows[Math.max(0, i - 1)];
		const d1   = rows[Math.min(rows.length - 1, i)];
		const d    = (!d1 || Math.abs(date - d0.dt) <= Math.abs(date - d1.dt)) ? d0 : d1;
		if (d.value === null || inGap(d.dt)) { hovered = null; return; }
		hovered    = { dt: d.dt, value: d.value, x: xScale(d.dt), y: yScale(d.value) };
	}
</script>

<div class="chart-wrap">
	{#if !rows.length}
		<p class="loading">Loading…</p>
	{:else}
		<svg
			bind:this={svgEl}
			width="100%"
			viewBox="0 0 {W} {H}"
			preserveAspectRatio="xMidYMid meet"
			style="cursor: default; display: block; width: 100%;"
		>
			{#if colourMode === 'gradient'}
				<defs>
					<linearGradient id="grad-{uid}" x1="0" y1={innerH} x2="0" y2="0"
						gradientUnits="userSpaceOnUse">
						<stop offset="0%"   stop-color="#DC4633" />
						<stop offset="25%"  stop-color="#F1C500" />
						<stop offset="100%" stop-color="#007FA3" />
					</linearGradient>
				</defs>
			{/if}

			<rect width={W} height={H} fill={T.bg} rx="6" />

			<!-- title / subtitle left-aligned to y-axis -->
			<text x={margin.left} y={24} font-family="TradeGothicBold, sans-serif" font-size="21" fill={T.title}>{title}</text>
			<text x={margin.left} y={52} font-family="OpenSans, sans-serif" font-size="12" fill={T.subtitle}>{subtitle}</text>

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

				<!-- gap overlays — render before data so data draws on top -->
				{#each gapRects as gr}
					<rect x={gr.x} y={0} width={gr.w} height={innerH}
						fill={T.gapFill} stroke="none" style="pointer-events: none" />
				{/each}

				<!-- hover crosshair -->
				{#if hovered}
					<line x1={hovered.x} x2={hovered.x} y1={0} y2={innerH} stroke={GRID_HOV} stroke-width="1" />
					<line x1={0} x2={hovered.x} y1={hovered.y} y2={hovered.y} stroke={GRID_HOV} stroke-width="1" stroke-dasharray="4,3" />
				{/if}

				<!-- daily dots — coloured by value in gradient mode, skip nulls -->
				{#each rows.filter((d) => d.value !== null) as d}
					<circle
						cx={xScale(d.dt)}
						cy={yScale(d.value)}
						r="1.5"
						fill={colourMode === 'gradient' && dotColourScale ? dotColourScale(d.value) : colour}
						opacity="0.28"
					/>
				{/each}

				<!-- 30-day avg line -->
				<path
					d={smoothPath}
					fill="none"
					stroke={colourMode === 'gradient' ? `url(#grad-${uid})` : colour}
					stroke-width="2.5"
					stroke-linejoin="round"
				/>

				<!-- two-line label centred on last smooth point -->
				{#if lineLabel}
					<text x={lineLabel.x} y={lineLabel.y - 7}  font-family="OpenSans, sans-serif" font-size="11" fill={colour}>30-day</text>
					<text x={lineLabel.x} y={lineLabel.y + 7}  font-family="OpenSans, sans-serif" font-size="11" fill={colour}>average</text>
				{/if}

				<!-- hovered dot highlight -->
				{#if hovered}
					<circle cx={hovered.x} cy={hovered.y} r="4"   fill={colour} />
					<circle cx={hovered.x} cy={hovered.y} r="6.5" fill="none" stroke={colour} stroke-width="1.5" opacity="0.5" />
				{/if}

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

				<!-- tooltip box -->
				{#if hovered}
					{@const bx = innerW - 168}
					{@const by = innerH - 74}
					<rect x={bx} y={by} width={163} height={57} rx="4" fill={T.tooltipBg} stroke={T.tooltipBd} stroke-width="1" />
					<text x={bx+12} y={by+19} font-family="OpenSans, sans-serif"     font-size="11" fill={T.tooltipDt}>{dateFmt(hovered.dt)}</text>
					<text x={bx+12} y={by+40} font-family="OpenSansBold, sans-serif" font-size="14" fill={T.tooltipVal}>{tooltipFmt(hovered.value)}</text>
				{/if}

				<!-- invisible overlay — crosshair cursor only in data area -->
				<rect role="presentation" x={0} y={0} width={innerW} height={innerH} fill="transparent" style="cursor: crosshair"
					onmousemove={onMouseMove} onmouseleave={() => (hovered = null)} />

			</g>
		</svg>
	{/if}
</div>

<style>
	.chart-wrap {
		max-width: 1060px;
		margin: 0 auto;
		padding: 0 20px;
	}
	.loading {
		text-align: center;
		color: #555;
		padding-top: 60px;
	}
</style>
