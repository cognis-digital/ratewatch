#!/usr/bin/env bash
# Offline walkthrough of ratewatch — no network, no API key required.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "== Treasury par-yield curve (offline sample) =="
python -m ratewatch yields --offline
echo
echo "== Fed funds effective rate (FRED sample) =="
python -m ratewatch series FEDFUNDS --offline
echo
echo "== CPI (FRED sample, JSON) =="
python -m ratewatch series CPIAUCSL --offline --format json
echo
echo "== Upcoming FOMC decisions =="
python -m ratewatch calendar --category FOMC --limit 3
