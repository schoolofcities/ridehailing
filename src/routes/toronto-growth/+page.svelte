<script>
	import { onMount } from 'svelte';
	import * as d3 from 'd3';
	import { base } from '$app/paths';
	import '$assets/global-styles.css';
	import TimeSeriesChart from '$lib/TimeSeriesChart.svelte';
	import StackedAreaChart from '$lib/StackedAreaChart.svelte';
	import { rollingMean } from '$lib/utils.js';
	import Password from '$lib/Password.svelte';

	let chart1Rows   = $state([]);
	let chart1Smooth = $state([]);
	let chart2Rows   = $state([]);
	let chart2Smooth = $state([]);
	let distRows     = $state([]);
	let chart4Rows   = $state([]);
	let chart4Smooth = $state([]);
	let xDomain      = $state(null);
	let theme        = $state('dark');

	// Known data-quality gaps: these days have 0/missing values across all fields.
	// They are excluded from all charts and smooth computations.
	const GAP_RANGES = [
		{ start: new Date('2021-10-07'), end: new Date('2021-10-09') },
		{ start: new Date('2021-10-14'), end: new Date('2021-10-16') },
		{ start: new Date('2025-05-26'), end: new Date('2025-05-28') }
	];

	function inGap(dt) {
		return GAP_RANGES.some((r) => dt >= r.start && dt <= r.end);
	}

	const revenueYFmt      = (v) => v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v/1e3).toFixed(0)}K` : `$${v}`;
	const revenueTooltipFmt = (v) => `$${Math.round(v).toLocaleString('en-CA')}`;

	// Build null-aware rows + smooth for a time series.
	// Gap days and zero-value days both become null; gap days are excluded from the rolling window.
	function buildSeries(all, getValue) {
		const rows = all.map((d) => {
			const v = getValue(d);
			return { dt: d.dt, value: (v > 0 && !inGap(d.dt)) ? v : null };
		});
		const valid = rows.filter((d) => d.value !== null);
		const smoothVals = rollingMean(valid.map((r) => r.value), 30);
		const smoothMap = new Map(valid.map((d, i) => [d.dt.getTime(), smoothVals[i]]));
		const smooth = rows.map((d) => ({ dt: d.dt, value: smoothMap.get(d.dt.getTime()) ?? null }));
		return { rows, smooth };
	}

	onMount(async () => {
		const raw = await fetch(`${base}/summary_stats.csv`).then((r) => r.text());

		const all = d3
			.csvParse(raw, (row) => ({
				dt:             new Date(row.dt),
				active_vehicles: +row.active_vehicles        || 0,
				dist_available:  +row.dist_available_routed  || 0,
				dist_enroute:    +row.dist_enroute_routed    || 0,
				dist_ontrip:     +row.dist_ontrip_routed     || 0,
				fare_avg:        +row.fare_avg               || 0,
				reported_trips:  +row.reported_trips_started || 0
			}))
			.filter((d) => d.dt && !isNaN(d.dt.getTime()) && d.dt.getFullYear() >= 2020);

		all.sort((a, b) => a.dt - b.dt);

		// Shared x-axis domain: full-year boundaries so all charts align on identical pixel columns.
		xDomain = [
			new Date(all[0].dt.getFullYear(), 0, 1),
			new Date(all[all.length - 1].dt.getFullYear() + 1, 0, 1)
		];

		// Chart 1 — active vehicles (null on gap days)
		const s1 = buildSeries(all, (d) => d.active_vehicles);
		chart1Rows   = s1.rows;
		chart1Smooth = s1.smooth;

		// Chart 2 — trips per day (null on gap days)
		const s2 = buildSeries(all, (d) => d.reported_trips);
		chart2Rows   = s2.rows;
		chart2Smooth = s2.smooth;

		// Chart 3 — stacked distance by phase (gap detection inside component)
		distRows = all.map((d) => ({
			dt:        d.dt,
			available: d.dist_available,
			enroute:   d.dist_enroute,
			ontrip:    d.dist_ontrip
		}));

		// Chart 4 — estimated daily revenue
		const s4 = buildSeries(all, (d) => (d.fare_avg > 0 && d.reported_trips > 0 ? d.fare_avg * d.reported_trips : 0));
		chart4Rows   = s4.rows;
		chart4Smooth = s4.smooth;
	});
</script>

<svelte:head>
	<title>Toronto ridehailing charts</title>
</svelte:head>

<Password />

<main class="page" class:light={theme === 'light'}>

	<div class="intro">
		<button
			class="theme-toggle"
			onclick={() => (theme = theme === 'dark' ? 'light' : 'dark')}
			aria-label="Toggle dark/light mode"
		>
			{theme === 'dark' ? '☀ Light mode' : '☾ Dark mode'}
		</button>

		<h2>Charting growth of ridehailing in Toronto</h2>
		<p>
			Visualizing increase in daily trips, active drivers, vehicle kilometres travelled, and fares paid for ridehailing services. <br><br>
			Data source: <a href="https://open.toronto.ca/dataset/private-transportation-companies-summary-and-trip-data/" target="_blank" rel="noopener">City of Toronto Open Data.</a>
		</p>
	</div>



	<TimeSeriesChart
		rows={chart2Rows}
		smooth={chart2Smooth}
		title="Increase in daily ridehailing trips"
		subtitle="Reported ridehailing trips started per day."
		darkColour="#F1C500"
		lightColour="#AB1368"
		{xDomain}
		gapRanges={GAP_RANGES}
		{theme}
	/>

	<div class="chart-gap"></div>

	<TimeSeriesChart
		rows={chart1Rows}
		smooth={chart1Smooth}
		title="Increase in daily active ridehailing vehicles"
		subtitle="Daily count of active ridehailing vehicles licensed in Toronto."
		darkColour="#8DBF2E"
		lightColour="#0D534D"
		{xDomain}
		gapRanges={GAP_RANGES}
		{theme}
	/>

	<div class="chart-gap"></div>

	<StackedAreaChart rows={distRows} {xDomain} gapRanges={GAP_RANGES} {theme} />

	<div class="chart-gap"></div>

	<TimeSeriesChart
		rows={chart4Rows}
		smooth={chart4Smooth}
		title="Increase in money spent on ridehailing"
		subtitle="Total fares per day ($)"
		colourMode="gradient"
		yTickFmt={revenueYFmt}
		tooltipFmt={revenueTooltipFmt}
		{xDomain}
		gapRanges={GAP_RANGES}
		{theme}
	/>

</main>

<style>
	:global(body) {
		background-color: #181818;
		transition: background-color 0.2s;
	}

	:global(body):has(.page.light) {
		background-color: #f7f7f7;
	}

	.page {
		padding: 0 0 20px;
	}

	.intro {
		max-width: 890px;
		margin: 0 auto;
		padding: 48px 20px 36px;
		text-align: center;
		margin-bottom: 50px;
		margin-top: 30px;
		position: relative;
	}

	.intro h2 {
		font-family: TradeGothicBold, sans-serif;
		font-size: 28px;
		color: #f0f0f0;
		margin: auto 0;
		margin-bottom: 20px;
		font-weight: normal;
		transition: color 0.2s;
	}

	.page.light .intro h2 {
		color: #111;
	}

	.intro p {
		font-family: OpenSans, serif;
		font-size: 16px;
		line-height: 26px;
		color: #dfdfdf;
		margin: 0 auto;
		transition: color 0.2s;
	}

	.page.light .intro p {
		color: #333;
	}

	.intro a {
		font-family: OpenSans, serif;
		color: inherit;
	}

	.intro a:hover {
		color: var(--brandYellow);
	}

	.page.light .intro a:hover {
		color: var(--brandMedBlue);
	}

	.chart-gap {
		height: 78px;
	}

	.theme-toggle {
		position: absolute;
		top: 48px;
		right: 20px;
		background: transparent;
		border: 1px solid rgba(255, 255, 255, 0.3);
		border-radius: 20px;
		color: #aaa;
		font-family: OpenSans, sans-serif;
		font-size: 12px;
		padding: 6px 14px;
		cursor: pointer;
		transition: border-color 0.2s, color 0.2s, background 0.2s;
	}

	.theme-toggle:hover {
		border-color: rgba(255, 255, 255, 0.6);
		color: #eee;
	}

	.page.light .theme-toggle {
		border-color: rgba(0, 0, 0, 0.25);
		color: #555;
	}

	.page.light .theme-toggle:hover {
		border-color: rgba(0, 0, 0, 0.5);
		color: #111;
	}
</style>
