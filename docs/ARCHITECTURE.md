# Architecture

`ratewatch` is a thin, standard-library-only CLI over two public macro data
sources plus a bundled calendar.

```
ratewatch/
  core.py        data model + fetch/parse/degrade logic (no import-time network)
  cli.py         argparse front-end; table & json renderers
  mcp_server.py  stdio JSON-RPC 2.0 MCP server exposing yields/series/calendar
  __main__.py    `python -m ratewatch`
  data/          bundled offline samples + calendar.json
```

## Data domains

| Domain   | Endpoint                                              | Auth | Format |
|----------|------------------------------------------------------|------|--------|
| Treasury | `home.treasury.gov/.../xml?data=daily_treasury_yield_curve` | none | Atom/XML |
| FRED     | `api.stlouisfed.org/fred/series/observations`        | free `FRED_API_KEY` | JSON |
| Calendar | bundled `data/calendar.json`                          | none | JSON |

## Degradation policy

Every fetch is fail-safe:

1. `--offline` (or no `FRED_API_KEY` for `series`) → bundled sample.
2. A live fetch that errors → bundled sample, with the `source` field annotated
   (`"treasury-sample (network unavailable)"`).
3. Only if no sample exists for an explicitly requested FRED series does the
   tool raise (`RateWatchError`) and exit non-zero.

This guarantees the CLI always produces useful output, online or off, and never
requires a secret to run.

## Treasury XML parsing

The Treasury feed is namespaced Atom/XML. The parser walks elements by
**local name** (`_local_name` strips the `{namespace}` prefix), so it is
resilient to namespace-URI churn. Each `<properties>` block becomes one
`YieldCurve`; curves are sorted ascending by date and the most recent is used.

## Secrets

The FRED key is read **only** from the `FRED_API_KEY` environment variable. No
credential is read from, or written to, any file in the repo. Bundled samples
contain only public economic numbers.
