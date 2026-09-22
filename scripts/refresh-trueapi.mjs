#!/usr/bin/env node
// Build-time reference refresh from the TrueAPI ingest Worker (warm KV only).
//
// midtermwatch.com's moat is the curated, hand-verified intake YAML — this script never
// writes to that pipeline. What it does produce is generated/trueapi-reference.json: the
// official Google Civic elections list and every FEC-declared 2026 congressional
// candidate, each with a fetchedAt stamp and a stale flag, so a build (or a reviewer)
// can cross-check the curated calendar against the live federal sources without either
// an API key or a single upstream call — the ingest Worker has already paid the quota.
//
// Usage: node scripts/refresh-trueapi.mjs
// Fails loudly on any miss so a half-reference never looks complete.

import { writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const INGEST = 'https://ingest.oakandmain.dev'

async function readEnvelope(path) {
  const response = await fetch(`${INGEST}${path}`, { signal: AbortSignal.timeout(30_000) })
  if (!response.ok) {
    throw new Error(`ingest ${path} → HTTP ${response.status} (${response.status === 404 ? 'cache_miss — feed not pre-warmed' : 'worker error'})`)
  }
  return response.json()
}

const OPENFEC_PAGES = ['S', 'H'].flatMap((office) =>
  Array.from({ length: 6 }, (_, i) => {
    const query = new URLSearchParams({
      per_page: '100', election_year: '2026', office, page: String(i + 1), sort: 'name',
    })
    return `/data/openfec/candidates/?${query}`
  }),
)

async function main() {
  const elections = await readEnvelope('/data/google-civic/elections')

  const candidates = []
  let fecFetchedAt = null
  let fecStale = false
  let fecReportedTotal = null
  for (const page of OPENFEC_PAGES) {
    const envelope = await readEnvelope(page)
    const results = Array.isArray(envelope.data?.results) ? envelope.data.results : []
    candidates.push(...results)
    fecFetchedAt = envelope.fetchedAt
    fecStale = fecStale || envelope.stale
    fecReportedTotal = envelope.data?.pagination?.count ?? fecReportedTotal
  }

  const byOffice = {}
  for (const candidate of candidates) {
    const key = candidate?.office === 'S' ? 'senate' : candidate?.office === 'H' ? 'house' : 'other'
    byOffice[key] = (byOffice[key] ?? 0) + 1
  }
  // The ingest feed set warms a fixed page budget; if FEC reports more declared
  // candidates than that, say so rather than presenting a partial list as complete.
  const truncated = fecReportedTotal !== null && candidates.length < fecReportedTotal

  const reference = {
    generated_at: new Date().toISOString(),
    sources: {
      google_civic: {
        elections: elections.data?.elections ?? [],
        fetched_at: elections.fetchedAt,
        stale: elections.stale,
        note: 'Google Civic Information API elections list (elections endpoints only — the retired Representatives path must never be called).',
      },
      openfec: {
        candidates_2026: candidates,
        counts: byOffice,
        total: candidates.length,
        reported_total: fecReportedTotal,
        truncated_by_feed_set: truncated,
        fetched_at: fecFetchedAt,
        stale: fecStale,
        note: 'FEC-declared 2026 congressional candidates; cross-check names/counts against curated intake, never overwrite it.',
      },
    },
  }

  const out = join(dirname(fileURLToPath(import.meta.url)), '..', 'generated', 'trueapi-reference.json')
  await writeFile(out, JSON.stringify(reference, null, 1))
  console.log(`✓ ${out} — civic elections: ${(elections.data?.elections ?? []).length}, FEC 2026 candidates: ${candidates.length} (S:${byOffice.senate ?? 0} H:${byOffice.house ?? 0})`)
}

main().catch((error) => {
  console.error(`✗ ${error.message}`)
  process.exit(1)
})
