// Gaussian-weighted rolling mean.
// sigma = win/5 keeps the half-width identical to a rectangular win-wide window
// but weights decay smoothly to ~zero at the edges, eliminating the "linear ramp"
// artefact that rectangular kernels produce around sharp data transitions (e.g. COVID).
export function rollingMean(values, win) {
	if (win <= 1) return [...values];
	const sigma   = win / 5;
	const half    = Math.ceil(win / 2);
	const weights = Array.from({ length: 2 * half + 1 }, (_, k) => {
		const x = k - half;
		return Math.exp(-0.5 * x * x / (sigma * sigma));
	});

	return values.map((_, i) => {
		let sum = 0, wsum = 0;
		for (let k = -half; k <= half; k++) {
			const j = i + k;
			if (j < 0 || j >= values.length) continue;
			const w = weights[k + half];
			sum  += values[j] * w;
			wsum += w;
		}
		return wsum > 0 ? sum / wsum : values[i];
	});
}
