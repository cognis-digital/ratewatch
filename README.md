# ratewatch — macro & rates CLI

> Part of the **[Cognis Neural Suite](https://github.com/cognis-digital)** by [Cognis Digital](https://cognis.digital)
> Cognis Open Collaboration License (COCL) v1.0 · domain: `fintech`

[![PyPI](https://img.shields.io/pypi/v/cognis-ratewatch.svg)](https://pypi.org/project/cognis-ratewatch/)
[![CI](https://github.com/cognis-digital/ratewatch/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/ratewatch/actions)
[![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE)
[![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

**Macro & rates CLI: Fed funds, CPI, Treasury yields, and key econ-calendar dates from public sources.**

`ratewatch` pulls **only public data** — the US Treasury Daily Par Yield Curve (public XML, no key) and the St. Louis Fed **FRED** time-series API (free key via the `FRED_API_KEY` environment variable, optional). With no key, or with `--offline`, it degrades gracefully to bundled sample data so it always produces output. Standard library only — no pip dependencies.

## Install

```bash
pip install cognis-ratewatch
# or, from this repo:
pip install -e ".[dev]"
```

## Quick start

```bash
ratewatch --version
ratewatch yields --offline                  # Treasury par-yield curve (bundled sample)
ratewatch yields                            # live Treasury curve (public, no key)
ratewatch series FEDFUNDS --offline         # Fed funds effective rate
ratewatch series CPIAUCSL                    # CPI (live if FRED_API_KEY set, else sample)
ratewatch calendar                          # upcoming FOMC / CPI / NFP dates
ratewatch calendar --category FOMC --limit 3
ratewatch yields --format json              # machine-readable
ratewatch mcp                               # expose as an MCP server
```

### FRED API key (optional)

The `series` subcommand uses a **free** FRED key when present:

```bash
export FRED_API_KEY=your_free_key_here       # get one at https://fred.stlouisfed.org
ratewatch series FEDFUNDS
```

No key committed anywhere — it is read only from the environment. Without it, `series` returns bundled sample data and says so in the `source` field.

## Subcommands

| Command    | Source                                              | Key |
|------------|-----------------------------------------------------|-----|
| `yields`   | US Treasury Daily Par Yield Curve (public XML)      | none |
| `series`   | FRED time series (e.g. `FEDFUNDS`, `CPIAUCSL`)      | free `FRED_API_KEY` (optional) |
| `calendar` | Bundled FOMC / CPI / NFP / GDP / PCE dates (JSON)   | none |

`--format table` (default) or `--format json`; `--out FILE` to write to disk; `--offline` to force bundled data.

## Offline demo

```bash
python -m ratewatch yields --offline
bash demos/01-basic/run.sh        # full offline walkthrough
```

See [`demos/01-basic/SCENARIO.md`](demos/01-basic/SCENARIO.md).

## Output formats

- **Table** (default) — human-readable terminal summary, including the 2s10s spread.
- **JSON** — machine-readable for pipelines and agents.

## Built on / data sources

- [US Treasury — Daily Treasury Par Yield Curve Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates) — public XML.
- [FRED — Federal Reserve Bank of St. Louis](https://fred.stlouisfed.org) — free API key.
- [BLS](https://www.bls.gov), [BEA](https://www.bea.gov), [Federal Reserve](https://www.federalreserve.gov) — release calendars.

Missing a credit? Open a PR.

## How it fits the Cognis Neural Suite

`ratewatch` is one tool in the [Cognis Neural Suite](https://github.com/cognis-digital). Every tool ships an MCP server, so [Cognis.Studio](https://cognis.studio) agents can call it as a scoped capability:

```json
{"command": "python", "args": ["-m", "ratewatch", "mcp"]}
```

## Architecture & roadmap

- Design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

## Responsible use

`ratewatch` reports public macroeconomic data for informational purposes only. It is **not investment advice**. Verify all figures against official sources before relying on them.

## About

**[Cognis Digital](https://cognis.digital)** — Wyoming, USA · *Making Tomorrow Better Today: Advanced Cybersecurity, AI Innovation, and Blockchain Expertise.*
