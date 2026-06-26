# Toronto Ridehailing

Interactive data visualizations to support a short research paper on ridehailing trends in Toronto. 

## Analysis

Preprocessing and exploratory data analysis scripts and notebooks are in `/analysis`. The data are from Open Data Toronto
[Open Data Toronto](https://open.toronto.ca/dataset/private-transportation-companies-summary-and-trip-data/). The data are quite large, so are not included in this repo, to run code, you'll have to add them to `/analysis/local_data`

## Interactive charts

Main code, using Svelte + D3, for the interactive charts is under `/src/routes/toronto-trends`

Built with Svelte and D3.

## Development

```bash
git clone https://github.com/schoolofcities/ridehailing
cd ridehailing
npm install
npm run dev
```

## Build

```bash
npm run build
```

Output goes to `docs/` for GitHub Pages deployment.
