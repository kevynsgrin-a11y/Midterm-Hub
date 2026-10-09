import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { importFromRepo } from './resolve-repo.mjs';

const root = new URL('../../', import.meta.url);
const payload = JSON.parse(readFileSync(new URL('generated/elections.json', root), 'utf8'));
const { downloads, downloadHref, formatBytes } = await importFromRepo('../../lib/downloads.ts');

test('the open-data page offers JSON, CSV and ICS', () => {
  assert.deepEqual(downloads.map((file) => file.format), ['JSON', 'CSV', 'ICS']);
});

test('every advertised download exists and matches its manifest entry', () => {
  for (const file of downloads) {
    const url = new URL(`public/downloads/${file.name}`, root);
    assert.ok(existsSync(url), `${file.name} is advertised but was not generated`);
    const bytes = readFileSync(url);
    assert.equal(bytes.length, file.bytes, `${file.name} size differs from the manifest`);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), file.sha256, `${file.name} differs from the manifest`);
  }
});

test('the JSON download is the edition payload and the CSV has one row per record', () => {
  const json = downloads.find((file) => file.format === 'JSON');
  const csv = downloads.find((file) => file.format === 'CSV');
  assert.deepEqual(JSON.parse(readFileSync(new URL(`public/downloads/${json.name}`, root), 'utf8')), payload);
  assert.equal(json.records, payload.elections.length);
  assert.equal(csv.records, payload.elections.length);
  // Notes are single-line, so a row is a line: header plus one per record.
  const lines = readFileSync(new URL(`public/downloads/${csv.name}`, root), 'utf8').trimEnd().split('\n');
  assert.equal(lines.length, payload.elections.length + 1);
});

test('download links add the base path only when one is configured', () => {
  assert.equal(downloadHref('a.csv', ''), '/downloads/a.csv');
  assert.equal(downloadHref('a.csv', '/Midterm-Hub'), '/Midterm-Hub/downloads/a.csv');
});

test('file sizes are shown in readable units', () => {
  assert.equal(formatBytes(512), '512 B');
  assert.equal(formatBytes(2048), '2.0 KB');
  assert.equal(formatBytes(3 * 1024 * 1024), '3.0 MB');
});
