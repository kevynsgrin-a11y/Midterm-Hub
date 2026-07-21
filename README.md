# civic-calendar-engine

A curation-first data pipeline for U.S. **off-cycle and local election** dates and
deadlines. It powers two products from one audited SQLite store:

1. a static, SEO-focused consumer directory of election dates/deadlines, and
2. versioned flat-file exports (CSV + changelog) sold to PACs, advocacy groups, and
   prediction markets.

**Accuracy is the entire product.** Every design decision protects data integrity:
deterministic identity, content hashing, an all-or-nothing intake, and — most
importantly — *verified data is never silently overwritten*. A conflicting re-ingest
of a verified record queues field-level changes for human review instead of clobbering
the confirmed value.

## What this is not

By design, the engine does **not** ingest live election-night results, integrate the
AP/DDHQ or Google Civic APIs, do address-to-ballot lookups, or serve HTTP. Output is
files only. If a source needs JavaScript to render, it is logged and left to manual
intake.

## Stack

Python 3.11+, stdlib `sqlite3` (WAL), Pydantic v2, Typer, httpx + tenacity
(Phase 2), BeautifulSoup4 + lxml (Phase 2), `icalendar`, PyYAML, pytest.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime + pytest
pip install -e .                      # exposes the `civic` command
```

## Quickstart

```bash
# 1. Create the database (data/civic.db by default).
civic init

# 2. Author (or reuse) an intake YAML file. The real curated 2026 dataset lives
#    in intake/ (every record cites an official source); a clearly-fake sample
#    for experiments ships in tests/fixtures/:
cat intake/2026-statewide.yaml
cat tests/fixtures/sample_intake.yaml

# 3. Validate + upsert the whole file (all-or-nothing).
civic intake tests/fixtures/sample_intake.yaml --by yourname

# 4. Inspect what landed. Everything ingests as `unverified`.
civic stats

# 5. Verify a record so it becomes exportable. Grab its id from stats/exports or:
#    civic export json --include-unverified   # to see ids in staging output
civic verify <ELECTION_ID> --by yourname

# 6. Export. By default exporters emit only VERIFIED records.
civic export json csv ics --version 2026.07.19
```

Exports land under `exports/` (git-ignored):

- `exports/json/{state}/index.json` and `exports/json/{state}/{slug}.json`
- `exports/csv/{version}/off_cycle_elections_{version}.csv` + `CHANGELOG.md`
- `exports/ics/{state}/{slug}.ics`

> Because exports are verified-only by default, run step 5 before step 6 or you will
> get an empty CSV (header only) and no JSON/ICS files. Use `--include-unverified`
> for staging builds; JSON then stamps `"includes_unverified": true`.

## The review workflow (why verified data is safe)

```bash
# A verified record exists. A curator re-ingests a file with a changed deadline:
civic intake updated_file.yaml

# The verified value is untouched; the change is queued:
civic review
#   <id>  VA  Town of Example — municipal (2027-05-04)
#     change 7: registration_deadline: '2027-04-12' → '2027-04-15'

civic approve 7      # apply the new value, recompute hash, restore `verified`
# or
civic reject 7       # discard the change, restore `verified`, value unchanged
```

## CLI reference

| Command | Purpose |
| --- | --- |
| `civic init` | Create the DB from `schema.sql` (idempotent). |
| `civic intake FILE.yaml` | Validate + upsert a YAML intake file. |
| `civic ingest --state VA \| --all` | Run state adapters (Phase 2). |
| `civic review` | List `needs_review` elections + pending changes. |
| `civic approve CHANGE_ID...` | Apply pending change(s). |
| `civic reject CHANGE_ID...` | Discard pending change(s). |
| `civic verify ELECTION_ID --by NAME` | Mark an election verified. |
| `civic export json\|csv\|ics [...]` | Produce exports (`--version`, `--out`, `--include-unverified`, `--since`). |
| `civic sources seed` | Load `seed/sources.yaml` into the sources table. |
| `civic site build [...]` | Generate the static consumer website (`--version`, `--out`, `--origin`, `--base-path`, `--include-unverified`, `--no-downloads`). |
| `civic stats` | Counts by state/status/type + pending-review count. |

## Data model

Records are keyed by a deterministic 16-hex id derived from
`{state}|{jurisdiction_slug}|{election_date}|{election_type}`, so the same real-world
election always maps to the same row (idempotent ingestion). A `content_hash` over the
substantive fields — never over provenance, status, or timestamps — decides whether a
re-ingest is a no-op, a safe update, or a review-gated conflict. See `schema.sql` and
`civic/ids.py`.

## Consumer website — "Plumbline"

Product #1 is a static, SEO-focused consumer directory generated from the verified
records by a hermetic static-site generator (`civic/site/`). It is files only — no
server — so it deploys to any static host.

```bash
civic site build --origin https://your-domain.example        # domain-root hosting
# or, for GitHub project-page hosting under a subpath:
civic site build --origin https://you.github.io --base-path /Midterm-Hub
```

Output (default `exports/site/`, git-ignored):

- `/` homepage, `/states/`, `/states/{ST}/`, `/elections/{ST}/{slug}/`,
  `/elections/{ST}/{slug}/{id}/`, `/about/`, `/methodology/`, `/data/`, `/404.html`
- `/sitemap.xml`, `/robots.txt`, hermetic `/assets/` (one CSS file, tiny vanilla JS,
  inline-SVG favicon)
- `/downloads/` — real JSON/CSV/ICS exports so the data links and calendar
  subscriptions work on the deployed site

Design & engineering notes:

- **Hermetic**: zero external requests — system fonts, inline SVG, no CDN/analytics.
- **Accessible**: WCAG 2.1 AA in light *and* dark; semantic landmarks, skip link,
  visible focus, and confidence encoded four ways (meter + label + color + border),
  never by color alone.
- **SEO**: per-page canonical/meta/Open Graph, schema.org JSON-LD (`Event`,
  `BreadcrumbList`, `WebSite`/`Organization`, `CollectionPage`, `Dataset`,
  `DefinedTermSet`), a real sitemap, and clean directory-style URLs.
- **Provenance-first**: every election page shows a source citation, confidence
  level, and verification metadata — accuracy rendered as UI.

`.github/workflows/pages.yml` builds and publishes the site to GitHub Pages on push
(derives the origin/subpath from the repo). Enable **Settings → Pages → Source:
GitHub Actions** once.

## Configuration (environment)

| Variable | Default |
| --- | --- |
| `CIVIC_DB_PATH` | `data/civic.db` |
| `CIVIC_EXPORT_DIR` | `exports/` |
| `CIVIC_RAW_DIR` | `data/raw/` |
| `CIVIC_USER_AGENT` | `CivicCalendarBot/0.1 (+https://example.com/bot)` |
| `CIVIC_ICS_DOMAIN` | `civic-calendar.local` |
| `CIVIC_RATE_LIMIT_SECONDS` | `2.0` |
| `CIVIC_SITE_ORIGIN` | `https://plumbline.example` |
| `CIVIC_SITE_BASE_PATH` | `` (empty = domain root) |

## Tests

```bash
pytest -q
```

`tests/test_store.py` (upsert semantics + the full review cycle) is the most important
file in the repo.

## Build phases

- **Phase 1 (implemented):** config, schema/db, ids, models, store, intake, JSON/CSV/ICS
  exporters, CLI, tests, CI. Fully useful with zero scrapers.
- **Phase 2:** polite `httpclient` with raw snapshots, the `StateAdapter` protocol, and
  fixture-backed VA/NJ/TX adapters feeding `civic ingest`; source seeding.
- **Phase 3:** deployment cron wrapper; per-client CSV packaging profiles.
