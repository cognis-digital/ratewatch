# Demo 01 — Reading the curve, a series, and the calendar (offline)

This scenario runs `ratewatch` entirely against **bundled sample data**, so it
needs no network access and no API key. It demonstrates all three data domains.

## Run it

```bash
# Treasury par-yield curve (human table, then JSON):
python -m ratewatch yields --offline
python -m ratewatch yields --offline --format json

# A FRED series — Fed funds effective rate, then CPI:
python -m ratewatch series FEDFUNDS --offline
python -m ratewatch series CPIAUCSL --offline --format json

# Upcoming macro calendar, filtered to FOMC meetings:
python -m ratewatch calendar --category FOMC --limit 3
```

Or run the whole walkthrough:

```bash
bash demos/01-basic/run.sh
```

## What you should see

- **yields** — a 1 Mo → 30 Yr par-yield curve for the latest bundled date,
  plus a `2s10s` spread line (e.g. `+40.0 bps (normal)`).
- **series FEDFUNDS** — a monthly Fed funds effective-rate history with the
  latest value highlighted; `source` reads `fred-sample` because no
  `FRED_API_KEY` is set.
- **calendar** — the next FOMC rate decisions with notes.

## Going live

Drop `--offline` to fetch the real Treasury curve (public, no key). Export a
free `FRED_API_KEY` to fetch real FRED series:

```bash
export FRED_API_KEY=your_free_key_here
python -m ratewatch series FEDFUNDS
```
