import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

export const prerender = true;

export function load() {
	redirect(301, `${base}/toronto-trends`);
}
