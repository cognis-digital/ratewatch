# ratewatch — macro & rates CLI

> Part of the **[Cognis Neural Suite](https://github.com/cognis-digital)** by [Cognis Digital](https://cognis.digital)
> Cognis Open Collaboration License (COCL) v1.0 · domain: `fintech`

[![PyPI](https://img.shields.io/pypi/v/cognis-ratewatch.svg)](https://pypi.org/project/cognis-ratewatch/)
[![CI](https://github.com/cognis-digital/ratewatch/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/ratewatch/actions)
[![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE)
[![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

**Macro & rates CLI: Fed funds, CPI, Treasury yields, and key econ-calendar dates from public sources.**

`ratewatch` pulls **only public data** — the US Treasury Daily Par Yield Curve (public XML, no key) and the St. Louis Fed **FRED** time-series API (free key via the `FRED_API_KEY` environment variable, optional). With no key, or with `--offline`, it degrades gracefully to bundled sample data so it always produces output. Standard library only — no pip dependencies.

<!-- cognis:domains:start -->

<!-- cognis:example:start -->
## 🔎 Example output

Real, reproducible output from the tool — runs offline:

```console
$ ratewatch-emit --version
ratewatch 0.1.0
```

```console
$ ratewatch-emit --help
usage: ratewatch [-h] [--version] {yields,series,calendar,mcp} ...

Macro & rates CLI — Fed funds, CPI, Treasury yields, and key econ-calendar
dates from public sources.

positional arguments:
  {yields,series,calendar,mcp}
    yields              Show the US Treasury par-yield curve.
    series              Show a FRED time series (e.g. FEDFUNDS, CPIAUCSL).
    calendar            Upcoming FOMC / CPI / NFP dates (bundled).
    mcp                 Run as an MCP server (stdio JSON-RPC).

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

> Blocks above are real `ratewatch` output — reproduce them from a clone.

**Sample result format** _(illustrative values — run on your own data for real findings):_

```
{
"findings": [
    {
        "id": "1234567890",
        "title": "Suspicious Network Traffic",
        "description": "Unusual network traffic detected from IP 192.168.1.100",
        "severity": "high",
        "created_at": "2023-02-20T14:30:00Z"
    },
    {
        "id": "2345678901",
        "title": "Malware Detection",
        "description": "Malware detected on host 192.168.1.101",
        "severity": "critical",
        "created_at": "2023-02-20T14:31:00Z"
    }
]
}
```

<!-- cognis:example:end -->

## Usage — step by step

1. **Install** from source (Python 3.9+):
   ```bash
   pip install .
   ```
2. **Show** the US Treasury par-yield curve (live, or `--offline` for bundled data):
   ```bash
   ratewatch yields --format table
   ```
3. **Fetch** a FRED time series (e.g. Fed funds, CPI):
   ```bash
   ratewatch series FEDFUNDS --limit 24 --format json
   ```
4. **Check** upcoming FOMC / CPI / NFP dates from the bundled calendar:
   ```bash
   ratewatch calendar --format json
   ```
5. **Automate** — write a report file for a dashboard or CI artifact:
   ```bash
   ratewatch yields --format html --out yields.html
   ```
   Also: `ratewatch mcp` (run as an MCP stdio server).

## Domains

**Primary domain:** Cyber & Security  ·  **JTF MERIDIAN division:** NULLBYTE · SPECTER

**Topics:** `cognis` `security` `infosec` `cybersecurity` `blue-team` `cli`

Part of the **Cognis Neural Suite** — 300+ source-available tools organized across 12 domains under the JTF MERIDIAN command structure. See the [suite on GitHub](https://github.com/cognis-digital) and [jtf-meridian](https://github.com/cognis-digital/jtf-meridian) for how the pieces fit together.
<!-- cognis:domains:end -->

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
ratewatch series DGS10 --offline            # 10-Year Treasury (preset)
ratewatch calendar                          # upcoming FOMC / CPI / NFP dates
ratewatch calendar --category FOMC --limit 3
ratewatch yields --format json              # machine-readable
ratewatch series DGS10 --format html --out dgs10.html   # styled HTML report
ratewatch mcp                               # expose as an MCP server
```

### Known FRED series presets

These ids carry a friendly label and ship with bundled offline sample data
(usable with `--offline` and no key):

| Series id  | Label |
|------------|-------|
| `FEDFUNDS` | Federal Funds Effective Rate |
| `CPIAUCSL` | Consumer Price Index (All Urban Consumers, All Items) |
| `DGS2`     | 2-Year Treasury Constant Maturity Rate |
| `DGS10`    | 10-Year Treasury Constant Maturity Rate |
| `T10Y2Y`   | 10-Year minus 2-Year Treasury Spread |
| `UNRATE`   | Unemployment Rate |
| `PCEPILFE` | Core PCE Price Index (excl. food & energy) |

Any other valid FRED series id also works (live with `FRED_API_KEY`).

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

`--format table` (default), `--format json`, or `--format html`; `--out FILE` to write to disk; `--offline` to force bundled data.

## Offline demo

```bash
python -m ratewatch yields --offline
bash demos/01-basic/run.sh        # full offline walkthrough
```

See [`demos/01-basic/SCENARIO.md`](demos/01-basic/SCENARIO.md).

## Output formats

- **Table** (default) — human-readable terminal summary, including the 2s10s spread.
- **JSON** — machine-readable for pipelines and agents.
- **HTML** — a self-contained, styled report (inline CSS, no JS/network) for `yields`, `series`, and `calendar`; the latest observation is highlighted. Pair with `--out report.html`.

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

## Interoperability

`ratewatch` composes with the 300+ tool Cognis suite — JSON in/out and a shared
OpenAI-compatible `/v1` backbone. See **[INTEROP.md](INTEROP.md)** for the
suite map, composition patterns, and reference stacks.

## Integrations

Forward `ratewatch`'s findings to STIX/MISP/Sigma/Splunk/Elastic/Slack/webhooks via
[`cognis-connect`](https://github.com/cognis-digital/cognis-connect). See **[INTEGRATIONS.md](INTEGRATIONS.md)**.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

## Responsible use

`ratewatch` reports public macroeconomic data for informational purposes only. It is **not investment advice**. Verify all figures against official sources before relying on them.

## About

**[Cognis Digital](https://cognis.digital)** — Wyoming, USA · *Making Tomorrow Better Today: Advanced Cybersecurity, AI Innovation, and Blockchain Expertise.*
